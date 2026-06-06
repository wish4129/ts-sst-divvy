#!/usr/bin/env python3
"""Correlation matrix — detect concentration risk across portfolio holdings.

Computes Pearson correlation between all pairs of held stocks using
2 years of daily returns. Flags pairs with correlation ≥ 0.8 as
concentration risk and warns when a persona holds correlated pairs.

Usage:
  cd ~/xiongit/divvy && .venv/bin/python3 scripts/risk/correlation.py
  cd ~/xiongit/divvy && .venv/bin/python3 scripts/risk/correlation.py --threshold 0.75
  cd ~/xiongit/divvy && .venv/bin/python3 scripts/risk/correlation.py --persona ares
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db import get_db
from persona_db import (
    get_all_stocks_dict,
    TICKER_TO_SHORT,
    SHORT_TO_TICKER,
)

try:
    import yfinance as yf
except ImportError:
    import os
    os.system(f"{sys.executable} -m pip install yfinance --quiet")
    import yfinance as yf

ROOT = Path(__file__).resolve().parent.parent.parent
MALAYSIA_TZ = timezone(timedelta(hours=8))
DEFAULT_THRESHOLD = 0.80
HISTORY_YEARS = 2.0


def fetch_returns_matrix(
    tickers: List[str],
    years: float = HISTORY_YEARS,
) -> Tuple[np.ndarray, List[str]]:
    """Fetch daily returns for a set of tickers.

    Returns:
        (returns_matrix, valid_tickers)
        returns_matrix: shape (n_days, n_stocks) — daily % returns
    """
    end = datetime.now()
    start = end - timedelta(days=int(years * 365) + 30)

    print(f"  Fetching {len(tickers)} stocks ({start.date()} → {end.date()})...")
    data = yf.download(
        tickers,
        start=start.strftime("%Y-%m-%d"),
        end=end.strftime("%Y-%m-%d"),
        progress=False,
        auto_adjust=True,
    )

    if data.empty:
        raise ValueError("yfinance returned empty data")

    close = data["Close"]
    returns_list = []
    valid_tickers = []

    for ticker in tickers:
        if ticker not in close.columns:
            continue
        prices = close[ticker].dropna().values
        if len(prices) < 60:
            continue
        daily_rets = (prices[1:] - prices[:-1]) / prices[:-1]
        returns_list.append(daily_rets)
        valid_tickers.append(ticker)

    if not returns_list:
        raise ValueError("No tickers with sufficient price data")

    min_len = min(len(r) for r in returns_list)
    returns_matrix = np.column_stack([r[:min_len] for r in returns_list])

    return returns_matrix, valid_tickers


def compute_correlation(
    returns: np.ndarray,
    tickers: List[str],
    threshold: float = DEFAULT_THRESHOLD,
) -> Dict:
    """Compute correlation matrix and flag high-correlation pairs.

    Args:
        returns: Daily returns matrix (n_days × n_stocks)
        tickers: Stock ticker codes (column order)
        threshold: Correlation coefficient above which pairs are flagged

    Returns:
        Dict with matrix, flagged pairs, and summary statistics.
    """
    n = returns.shape[1]
    corr_matrix = np.corrcoef(returns, rowvar=False)

    # Extract upper triangle (excluding diagonal)
    high_pairs = []
    for i in range(n):
        for j in range(i + 1, n):
            corr = float(corr_matrix[i, j])
            if abs(corr) >= threshold:
                high_pairs.append({
                    "stock_a": tickers[i],
                    "stock_b": tickers[j],
                    "correlation": round(corr, 4),
                    "strength": _correlation_strength(corr),
                })

    high_pairs.sort(key=lambda p: abs(p["correlation"]), reverse=True)

    # Statistics
    upper_tri = corr_matrix[np.triu_indices(n, k=1)]
    mean_corr = float(np.mean(upper_tri))
    median_corr = float(np.median(upper_tri))
    min_corr = float(np.min(upper_tri))
    max_corr = float(np.max(upper_tri))

    # Build full matrix as nested dict for JSON
    matrix_json = {}
    for i, ticker_a in enumerate(tickers):
        row = {}
        for j, ticker_b in enumerate(tickers):
            if i < j:
                row[ticker_b] = round(float(corr_matrix[i, j]), 4)
        if row:
            matrix_json[ticker_a] = row

    return {
        "n_stocks": n,
        "mean_correlation": round(mean_corr, 4),
        "median_correlation": round(median_corr, 4),
        "min_correlation": round(min_corr, 4),
        "max_correlation": round(max_corr, 4),
        "threshold": threshold,
        "n_high_pairs": len(high_pairs),
        "high_correlation_pairs": high_pairs,
        "pct_high_correlation": round(len(high_pairs) / max(1, n * (n - 1) / 2) * 100, 1),
        "matrix": matrix_json,
    }


def _correlation_strength(corr: float) -> str:
    """Classify correlation strength."""
    a = abs(corr)
    if a >= 0.9:
        return "very strong" + (" positive" if corr > 0 else " negative")
    elif a >= 0.8:
        return "strong" + (" positive" if corr > 0 else " negative")
    elif a >= 0.6:
        return "moderate" + (" positive" if corr > 0 else " negative")
    elif a >= 0.4:
        return "weak" + (" positive" if corr > 0 else " negative")
    else:
        return "negligible"


def check_persona_concentration(
    persona_id: str,
    holdings: List[str],  # list of short names
    high_pairs: List[Dict],
    short_to_ticker: Dict[str, str],
    ticker_to_short: Dict[str, str],
) -> List[Dict]:
    """Check if a persona's holdings contain highly correlated pairs.

    Returns list of concentration warnings.
    """
    # Convert persona holdings to ticker codes
    holding_tickers = set()
    for name in holdings:
        ticker = short_to_ticker.get(name, name + ".KL")
        holding_tickers.add(ticker)

    warnings = []
    for pair in high_pairs:
        a, b = pair["stock_a"], pair["stock_b"]
        if a in holding_tickers and b in holding_tickers:
            short_a = ticker_to_short.get(a, a.replace(".KL", ""))
            short_b = ticker_to_short.get(b, b.replace(".KL", ""))
            warnings.append({
                "stock_a": short_a,
                "stock_b": short_b,
                "ticker_a": a,
                "ticker_b": b,
                "correlation": pair["correlation"],
                "strength": pair["strength"],
                "risk": _concentration_risk_level(pair["correlation"]),
            })

    return warnings


def _concentration_risk_level(corr: float) -> str:
    """Translate correlation to risk level."""
    a = abs(corr)
    if a >= 0.9:
        return "CRITICAL — near-identical moves, diversify immediately"
    elif a >= 0.85:
        return "HIGH — significant concentration risk"
    elif a >= 0.80:
        return "ELEVATED — monitor and consider reducing one position"
    else:
        return "MODERATE"


def load_persona_holdings() -> Dict[str, List[str]]:
    """Get current holdings per persona from DB.

    Returns {persona_id: [short_name, ...]}
    """
    db = get_db()
    cur = db.cursor()
    cur.execute(
        """SELECT up.persona, ph.stock_id
           FROM portfolio_holdings ph
           JOIN user_portfolios up ON up.id = ph.portfolio_id
           WHERE ph.shares >= 100"""
    )
    holdings = {"ares": [], "demeter": [], "athena": []}
    for row in cur.fetchall():
        pid = row[0]
        ticker = row[1]
        short = TICKER_TO_SHORT.get(ticker, ticker.replace(".KL", ""))
        if pid in holdings:
            holdings[pid].append(short)
    cur.close()
    db.close()
    return holdings


# ── Main ────────────────────────────────────────────────────────────

def run_correlation(
    persona_id: Optional[str] = None,
    threshold: float = DEFAULT_THRESHOLD,
    years: float = HISTORY_YEARS,
) -> Dict:
    """Run correlation analysis for one or all personas.

    Returns:
        Dict with correlation matrix, high pairs, and per-persona warnings.
    """
    print(f"\n{'='*60}")
    print(f"Correlation Matrix — Concentration Risk Analysis")
    print(f"Threshold: ≥{threshold:.0%} | {years}yr daily returns")
    print(f"{'='*60}")

    # Get all stocks in the universe
    all_stocks = get_all_stocks_dict()
    ticker_set = set(info["code"] for info in all_stocks.values())
    tickers = sorted(ticker_set)

    # Fetch returns
    returns_matrix, valid_tickers = fetch_returns_matrix(tickers, years)

    # Compute correlation
    corr_results = compute_correlation(returns_matrix, valid_tickers, threshold)

    print(f"\n  {corr_results['n_stocks']} stocks analyzed")
    print(f"  Mean correlation: {corr_results['mean_correlation']:.4f}")
    print(f"  Median correlation: {corr_results['median_correlation']:.4f}")
    print(f"  Range: [{corr_results['min_correlation']:.4f}, {corr_results['max_correlation']:.4f}]")
    print(f"  High-correlation pairs (≥{threshold:.0%}): {corr_results['n_high_pairs']} "
          f"({corr_results['pct_high_correlation']}%)")

    if corr_results["high_correlation_pairs"]:
        print(f"\n  ⚠️  Top 10 correlated pairs:")
        for pair in corr_results["high_correlation_pairs"][:10]:
            a = pair["stock_a"].replace(".KL", "")
            b = pair["stock_b"].replace(".KL", "")
            bar = "█" * min(10, int(abs(pair["correlation"]) * 10))
            print(f"    {a:6s} ↔ {b:6s}  r={pair['correlation']:.3f}  {bar}  {pair['strength']}")

    # Load current portfolio holdings
    persona_holdings = load_persona_holdings()
    short_to_ticker = SHORT_TO_TICKER
    ticker_to_short = TICKER_TO_SHORT

    # Check each persona
    personas_to_check = [persona_id] if persona_id else ["ares", "demeter", "athena"]
    persona_warnings = {}

    for pid in personas_to_check:
        holdings = persona_holdings.get(pid, [])
        if not holdings:
            print(f"\n  [{pid.upper()}] No holdings")
            persona_warnings[pid] = {"warnings": [], "holdings": []}
            continue

        warnings = check_persona_concentration(
            pid, holdings, corr_results["high_correlation_pairs"],
            short_to_ticker, ticker_to_short,
        )

        persona_warnings[pid] = {
            "holdings": holdings,
            "n_holdings": len(holdings),
            "n_warnings": len(warnings),
            "warnings": warnings,
        }

        if warnings:
            print(f"\n  [{pid.upper()}] ⚠️  {len(warnings)} concentration warning(s) — {len(holdings)} holdings:")
            for w in warnings:
                print(f"    {w['stock_a']:8s} ↔ {w['stock_b']:8s}  "
                      f"r={w['correlation']:.3f}  {w['risk']}")
        else:
            print(f"\n  [{pid.upper()}] ✓ No concentration risk — {len(holdings)} holdings well-diversified")

    return {
        "correlation": corr_results,
        "personas": persona_warnings,
        "threshold": threshold,
        "years": years,
    }


def main():
    persona = None
    threshold = DEFAULT_THRESHOLD
    years = HISTORY_YEARS

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        arg = args[i]
        if arg.startswith("--persona="):
            persona = arg.split("=", 1)[1]
        elif arg == "--persona" and i + 1 < len(args):
            i += 1; persona = args[i]
        elif arg.startswith("--threshold="):
            threshold = float(arg.split("=", 1)[1])
        elif arg == "--threshold" and i + 1 < len(args):
            i += 1; threshold = float(args[i])
        elif arg.startswith("--years="):
            years = float(arg.split("=", 1)[1])
        elif arg == "--years" and i + 1 < len(args):
            i += 1; years = float(args[i])
        i += 1

    results = run_correlation(persona_id=persona, threshold=threshold, years=years)

    # Save results
    output_path = ROOT / "data" / "correlation_matrix.json"
    output = {
        "generated_at": datetime.now(MALAYSIA_TZ).isoformat(),
        "threshold": threshold,
        "years": years,
        **results,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # Save without full matrix (too large for summary) but keep top-level
    matrix = output.pop("correlation", {})
    output["correlation_summary"] = {
        k: v for k, v in matrix.items() if k != "matrix"
    }
    output["correlation"] = matrix

    output_path.write_text(json.dumps(output, indent=2))
    print(f"\n  ✓ Results saved to {output_path}")

    # Summary
    total_warnings = sum(
        pw["n_warnings"] for pw in output.get("personas", {}).values()
    )
    print(f"\n{'='*60}")
    print(f"Total concentration warnings across personas: {total_warnings}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
