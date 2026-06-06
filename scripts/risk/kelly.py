#!/usr/bin/env python3
"""Kelly criterion position sizing — risk-adjusted allocation based on edge.

Computes the Kelly fraction for each stock: the optimal percentage of
capital to allocate given win probability and win/loss ratio. Uses
historical daily returns to estimate edge, then applies Half-Kelly
for conservative position sizing.

Formula: f* = (bp - q) / b  where:
  b = avg_win / avg_loss (odds ratio)
  p = win rate (fraction of positive return days)
  q = 1 - p
  f* = optimal fraction of capital to risk

Half-Kelly (f*/2) is used as the recommended allocation — safer and
less volatile than full Kelly.

Usage:
  cd ~/xiongit/divvy && .venv/bin/python3 scripts/risk/kelly.py
  cd ~/xiongit/divvy && .venv/bin/python3 scripts/risk/kelly.py --half
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from persona_db import (
    get_all_stocks_dict,
    TICKER_TO_SHORT,
    SHORT_TO_TICKER,
)
from strategies.sector_limits import get_sector, SECTOR_LIMIT

try:
    import yfinance as yf
except ImportError:
    import os
    os.system(f"{sys.executable} -m pip install yfinance --quiet")
    import yfinance as yf

ROOT = Path(__file__).resolve().parent.parent.parent
MALAYSIA_TZ = timezone(timedelta(hours=8))
HISTORY_YEARS = 2.0
MAX_KELLY_FRACTION = 0.25  # Cap Kelly at 25% even if formula suggests more


def compute_kelly_fraction(
    returns: np.ndarray,
    half_kelly: bool = True,
) -> Tuple[float, float, float, float]:
    """Compute Kelly fraction from daily returns.

    Args:
        returns: 1D array of daily returns
        half_kelly: If True, return f*/2 (more conservative)

    Returns:
        (kelly_fraction, win_rate, win_loss_ratio, edge_pct)
    """
    if len(returns) < 20:
        return 0.0, 0.0, 0.0, 0.0

    # Separate wins and losses
    wins = returns[returns > 0]
    losses = returns[returns < 0]

    if len(wins) == 0 or len(losses) == 0:
        return 0.0, 0.0, 0.0, 0.0

    p = len(wins) / len(returns)  # Win probability
    q = 1.0 - p

    avg_win = np.mean(wins)
    avg_loss = abs(np.mean(losses))

    if avg_loss == 0:
        return 0.0, p, 0.0, 0.0

    b = avg_win / avg_loss  # Odds ratio (win/loss)

    if b <= 0:
        return 0.0, p, b, 0.0

    # Kelly formula: f* = (bp - q) / b
    f_star = (b * p - q) / b

    # Edge = expected return per unit bet
    edge = (b * p - q) * 100

    # Negative Kelly means no edge — don't bet
    if f_star <= 0:
        return 0.0, p, b, edge

    # Half-Kelly is standard practice
    if half_kelly:
        f_star = f_star / 2.0

    # Cap at maximum
    f_star = min(f_star, MAX_KELLY_FRACTION)

    return f_star, p, b, edge


def fetch_daily_returns(
    tickers: List[str],
    years: float = HISTORY_YEARS,
) -> Dict[str, np.ndarray]:
    """Fetch daily returns for all tickers.

    Returns {ticker: daily_returns_array}
    """
    end = datetime.now()
    start = end - timedelta(days=int(years * 365) + 30)

    data = yf.download(
        tickers,
        start=start.strftime("%Y-%m-%d"),
        end=end.strftime("%Y-%m-%d"),
        progress=False,
        auto_adjust=True,
    )

    if data.empty:
        return {}

    close = data["Close"]
    result = {}

    for ticker in tickers:
        if ticker not in close.columns:
            continue
        prices = close[ticker].dropna().values
        if len(prices) < 60:
            continue
        daily_rets = (prices[1:] - prices[:-1]) / prices[:-1]
        result[ticker] = daily_rets

    return result


def compute_portfolio_kelly(
    returns_dict: Dict[str, np.ndarray],
    ticker_to_short: Dict[str, str],
    half_kelly: bool = True,
) -> List[Dict]:
    """Compute Kelly fractions for all stocks and rank them.

    Returns sorted list of {stock, ticker, kelly_pct, win_rate, win_loss_ratio, edge}.
    """
    results = []
    for ticker, rets in returns_dict.items():
        f_star, win_rate, wl_ratio, edge = compute_kelly_fraction(rets, half_kelly)
        short = ticker_to_short.get(ticker, ticker.replace(".KL", ""))
        sector = get_sector(short)

        if f_star > 0:
            kelly_label = _kelly_label(f_star)
        else:
            kelly_label = "No edge — avoid"

        results.append({
            "stock": short,
            "ticker": ticker,
            "sector": sector,
            "kelly_fraction_pct": round(f_star * 100, 1),
            "win_rate_pct": round(win_rate * 100, 1),
            "win_loss_ratio": round(wl_ratio, 2),
            "edge_pct": round(edge, 2),
            "recommendation": kelly_label,
            "data_points": len(rets),
        })

    results.sort(key=lambda x: x["kelly_fraction_pct"], reverse=True)
    return results


def _kelly_label(f_star: float) -> str:
    """Human-readable Kelly recommendation."""
    if f_star >= 0.20:
        return "Heavy allocation — strong edge"
    elif f_star >= 0.10:
        return "Standard position — good edge"
    elif f_star >= 0.05:
        return "Moderate position — modest edge"
    elif f_star > 0:
        return "Small position — marginal edge"
    else:
        return "No edge — avoid"


def compute_persona_kelly_allocations(
    holdings: Dict[str, dict],  # {short_name: {shares, cost, ...}}
    returns_dict: Dict[str, np.ndarray],
    persona_id: str,
    max_single: float = 0.25,
    half_kelly: bool = True,
) -> Dict:
    """Compute Kelly-optimal allocations for a persona's holdings.

    Normalizes Kelly fractions so they sum to ≤ 1.0, respecting max
    single position constraint.

    Returns {stock: suggested_allocation_pct, ...} and summary.
    """
    kelly_scores = {}
    total_kelly = 0.0

    for short, h in holdings.items():
        ticker = SHORT_TO_TICKER.get(short, short + ".KL")
        rets = returns_dict.get(ticker)
        if rets is None or len(rets) < 60:
            kelly_scores[short] = 0.0
            continue

        f_star, _, _, _ = compute_kelly_fraction(rets, half_kelly)
        # Clamp to max single position
        f_star = min(f_star, max_single)
        kelly_scores[short] = f_star
        total_kelly += f_star

    # Normalize if total > 1.0
    allocations = {}
    if total_kelly > 0:
        scale = min(1.0, 1.0 / total_kelly) if total_kelly > 1.0 else 1.0
        for short, f in kelly_scores.items():
            allocations[short] = round(f * scale * 100, 1)

    return {
        "persona": persona_id,
        "half_kelly": half_kelly,
        "max_single_position_pct": round(max_single * 100, 0),
        "allocations": allocations,
        "n_positive_edge": sum(1 for f in kelly_scores.values() if f > 0),
    }


def load_persona_holdings() -> Dict[str, Dict[str, dict]]:
    """Get current holdings per persona from DB."""
    from db import get_db
    db = get_db()
    cur = db.cursor()
    cur.execute(
        """SELECT up.persona, ph.stock_id, ph.shares, ph.avg_cost
           FROM portfolio_holdings ph
           JOIN user_portfolios up ON up.id = ph.portfolio_id
           WHERE ph.shares >= 100"""
    )
    holdings = {"ares": {}, "demeter": {}, "athena": {}}
    for row in cur.fetchall():
        pid = row[0]
        ticker = row[1]
        short = TICKER_TO_SHORT.get(ticker, ticker.replace(".KL", ""))
        holdings[pid][short] = {
            "shares": row[2],
            "cost": float(row[3]),
        }
    cur.close()
    db.close()
    return holdings


# ── Main ────────────────────────────────────────────────────────────

def run_kelly_analysis(
    half_kelly: bool = True,
    years: float = HISTORY_YEARS,
) -> Dict:
    """Run Kelly criterion analysis for all stocks and personas.

    Returns:
        Dict with ranked stocks and per-persona allocations.
    """
    method = "Half-Kelly" if half_kelly else "Full Kelly"
    print(f"\n{'='*60}")
    print(f"Kelly Criterion Position Sizing — {method}")
    print(f"{'='*60}")

    # Get all stocks
    all_stocks = get_all_stocks_dict()
    tickers = sorted(set(info["code"] for info in all_stocks.values()))

    # Fetch returns
    print(f"\n  Fetching {len(tickers)} stocks...")
    returns_dict = fetch_daily_returns(tickers, years)
    print(f"  Got returns for {len(returns_dict)}/{len(tickers)} stocks")

    # Compute Kelly for all stocks
    ticker_to_short = {info["code"]: short for short, info in all_stocks.items()}
    ranked = compute_portfolio_kelly(returns_dict, ticker_to_short, half_kelly)

    # Display top stocks
    print(f"\n  Top 10 stocks by Kelly fraction:")
    positive = [r for r in ranked if r["kelly_fraction_pct"] > 0]
    negative = [r for r in ranked if r["kelly_fraction_pct"] == 0]

    for r in positive[:10]:
        bar = "█" * min(10, int(r["kelly_fraction_pct"] / 2.5))
        print(f"    {r['stock']:8s}  {r['kelly_fraction_pct']:5.1f}%  {bar}  "
              f"W={r['win_rate_pct']:.0f}%  W/L={r['win_loss_ratio']:.2f}  "
              f"Edge={r['edge_pct']:+.1f}%  {r['recommendation']}")

    print(f"\n  {len(positive)} stocks with positive edge, {len(negative)} with no edge")

    # Per-persona allocations
    persona_holdings = load_persona_holdings()
    persona_results = {}

    max_positions = {"ares": 0.25, "demeter": 0.35, "athena": 0.30}

    for pid in ["ares", "demeter", "athena"]:
        holdings = persona_holdings.get(pid, {})
        if not holdings:
            continue

        result = compute_persona_kelly_allocations(
            holdings, returns_dict, pid,
            max_single=max_positions[pid],
            half_kelly=half_kelly,
        )

        persona_results[pid] = result

        print(f"\n  [{pid.upper()}] Kelly-optimal allocations ({len(result['allocations'])} holdings):")
        for stock, pct in sorted(result["allocations"].items(), key=lambda x: x[1], reverse=True):
            current = holdings.get(stock, {})
            kelly = compute_kelly_fraction(
                returns_dict.get(SHORT_TO_TICKER.get(stock, stock + ".KL"), np.array([])),
                half_kelly,
            )
            print(f"    {stock:10s}  {pct:5.1f}%  "
                  f"(Kelly edge: {kelly[3]:+.1f}%, W/L: {kelly[2]:.2f})")

    return {
        "method": method,
        "half_kelly": half_kelly,
        "all_stocks_ranked": ranked,
        "personas": persona_results,
        "n_stocks_with_edge": len(positive),
        "n_stocks_no_edge": len(negative),
    }


def main():
    half_kelly = "--full" not in sys.argv  # Half-Kelly by default

    results = run_kelly_analysis(half_kelly=half_kelly)

    # Save results
    output_path = ROOT / "data" / "kelly_allocations.json"
    output = {
        "generated_at": datetime.now(MALAYSIA_TZ).isoformat(),
        **results,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2))
    print(f"\n  ✓ Results saved to {output_path}")


if __name__ == "__main__":
    main()
