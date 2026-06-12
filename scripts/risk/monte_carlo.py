#!/usr/bin/env python3
"""Monte Carlo position sizing — find optimal stock allocations via simulation.

Runs N random portfolio weight simulations, computes expected return,
volatility, and Sharpe ratio for each, then identifies the maximum-Sharpe
and minimum-variance portfolios.

For each persona, outputs suggested position sizes as percentage of
portfolio value, respecting persona constraints (max single position,
min stock count).

Usage:
  cd ~/xiongit/divvy && .venv/bin/python3 scripts/risk/monte_carlo.py
  cd ~/xiongit/divvy && .venv/bin/python3 scripts/risk/monte_carlo.py --sims 2000
  cd ~/xiongit/divvy && .venv/bin/python3 scripts/risk/monte_carlo.py --persona ares
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

try:
    import yfinance as yf
except ImportError:
    import os
    os.system(f"{sys.executable} -m pip install yfinance --quiet")
    import yfinance as yf

ROOT = Path(__file__).resolve().parent.parent.parent
MALAYSIA_TZ = timezone(timedelta(hours=8))

# Persona position constraints
PERSONA_LIMITS = {
    "ares": {"max_single_position": 0.25, "min_stocks": 4},
    "demeter": {"max_single_position": 0.35, "min_stocks": 4},
    "athena": {"max_single_position": 0.30, "min_stocks": 5},
}

DEFAULT_SIMULATIONS = 1000
RISK_FREE_RATE = 0.03   # Malaysia OPR ≈ 3%
TRADING_DAYS = 252


def fetch_returns(
    tickers: List[str],
    years: float = 2.0,
) -> Tuple[np.ndarray, List[str], np.ndarray]:
    """Fetch daily returns for a set of tickers.

    Returns:
        (returns_matrix, ticker_labels, mean_daily_returns)
        returns_matrix: shape (n_trading_days-1, n_stocks) — daily % returns
        ticker_labels: list of ticker codes (column order)
        mean_daily_returns: shape (n_stocks,) — mean daily return per stock
    """
    end = datetime.now()
    start = end - timedelta(days=int(years * 365) + 30)

    print(f"  Fetching prices for {len(tickers)} stocks ({start.date()} → {end.date()})...")
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

    # Build returns matrix
    returns_list = []
    valid_tickers = []

    for ticker in tickers:
        if ticker not in close.columns:
            continue
        prices = close[ticker].dropna().values
        if len(prices) < 60:  # Need at least ~3 months
            continue
        # Daily returns: (p[t] - p[t-1]) / p[t-1]
        daily_rets = (prices[1:] - prices[:-1]) / prices[:-1]
        returns_list.append(daily_rets)
        valid_tickers.append(ticker)

    if not returns_list:
        raise ValueError("No tickers with sufficient price data")

    # Align to the same length (take min to avoid NaN)
    min_len = min(len(r) for r in returns_list)
    returns_matrix = np.column_stack([r[:min_len] for r in returns_list])
    mean_returns = np.mean(returns_matrix, axis=0)

    print(f"  {len(valid_tickers)} stocks × {min_len} trading days")
    return returns_matrix, valid_tickers, mean_returns


def simulate_portfolios(
    returns: np.ndarray,
    n_simulations: int = DEFAULT_SIMULATIONS,
    max_weight: float = 0.35,
    min_stocks: int = 4,
    risk_free: float = RISK_FREE_RATE,
) -> Dict:
    """Run Monte Carlo portfolio simulations.

    For each simulation:
    1. Generate random weights summing to 1
    2. Enforce max single position constraint
    3. Enforce minimum stock count
    4. Compute portfolio return, volatility, Sharpe

    Args:
        returns: Daily returns matrix (n_days × n_stocks)
        n_simulations: Number of random portfolios to test
        max_weight: Maximum weight for any single stock
        min_stocks: Minimum number of stocks with non-zero weight
        risk_free: Annual risk-free rate (decimal)

    Returns:
        Dict with simulation results and optimal portfolios.
    """
    n_stocks = returns.shape[1]
    mean_daily = np.mean(returns, axis=0)
    cov_matrix = np.cov(returns, rowvar=False)

    # Storage
    sim_returns = np.zeros(n_simulations)
    sim_vols = np.zeros(n_simulations)
    sim_sharpes = np.zeros(n_simulations)
    sim_weights = np.zeros((n_simulations, n_stocks))

    rng = np.random.default_rng(42)  # Reproducible

    for i in range(n_simulations):
        # Generate random weights (Dirichlet distribution for sum-to-1)
        weights = rng.dirichlet(np.ones(n_stocks))

        # Enforce max single position
        weights = np.clip(weights, 0, max_weight)

        # Enforce minimum stock count (zero out smallest weights)
        mask = weights > 0.001  # Consider >0.1% as "held"
        n_held = np.sum(mask)
        if n_held > 0 and n_held < min_stocks and n_stocks >= min_stocks:
            # Keep the top min_stocks, zero out the rest
            threshold = np.partition(weights, -min_stocks)[-min_stocks]
            weights[weights < threshold] = 0

        # Renormalize iteratively, clipping to max_weight each pass.
        # Without iteration, renorm can push clipped weights back above max_weight
        # because the sum of clipped weights is < 1, and dividing inflates them.
        total = weights.sum()
        if total > 0:
            for _ in range(10):  # converge: clip → normalize → repeat
                weights = weights / max(total, 1e-10)
                weights = np.clip(weights, 0, max_weight)
                total = weights.sum()
                if total <= 0:
                    weights = np.ones(n_stocks) / n_stocks
                    break
            # Final normalize after clipping
            total = weights.sum()
            weights = weights / total if total > 0 else np.ones(n_stocks) / n_stocks
            # One last clip as safety net
            weights = np.clip(weights, 0, max_weight)
            total = weights.sum()
            weights = weights / total if total > 0 else np.ones(n_stocks) / n_stocks
        else:
            weights = np.ones(n_stocks) / n_stocks

        sim_weights[i] = weights

        # Portfolio metrics
        port_return = np.dot(mean_daily, weights) * TRADING_DAYS
        port_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights))) * np.sqrt(TRADING_DAYS)
        port_sharpe = (port_return - risk_free) / port_vol if port_vol > 0 else 0

        sim_returns[i] = port_return
        sim_vols[i] = port_vol
        sim_sharpes[i] = port_sharpe

    # Find optimal portfolios
    max_sharpe_idx = np.argmax(sim_sharpes)
    min_vol_idx = np.argmin(sim_vols)

    optimal_weights = sim_weights[max_sharpe_idx]
    minvar_weights = sim_weights[min_vol_idx]

    # Statistics
    return {
        "n_simulations": n_simulations,
        "sim_returns": sim_returns.tolist(),
        "sim_volatilities": sim_vols.tolist(),
        "sim_sharpes": sim_sharpes.tolist(),
        "optimal_portfolio": {
            "weights": optimal_weights.tolist(),
            "expected_return_pct": round(float(sim_returns[max_sharpe_idx]) * 100, 2),
            "volatility_pct": round(float(sim_vols[max_sharpe_idx]) * 100, 2),
            "sharpe_ratio": round(float(sim_sharpes[max_sharpe_idx]), 3),
        },
        "min_variance_portfolio": {
            "weights": minvar_weights.tolist(),
            "expected_return_pct": round(float(sim_returns[min_vol_idx]) * 100, 2),
            "volatility_pct": round(float(sim_vols[min_vol_idx]) * 100, 2),
            "sharpe_ratio": round(float(sim_sharpes[min_vol_idx]), 3),
        },
        "sharpe_pctiles": {
            "p25": round(float(np.percentile(sim_sharpes, 25)), 3),
            "p50": round(float(np.percentile(sim_sharpes, 50)), 3),
            "p75": round(float(np.percentile(sim_sharpes, 75)), 3),
            "p90": round(float(np.percentile(sim_sharpes, 90)), 3),
        },
        "mean_sharpe": round(float(np.mean(sim_sharpes)), 3),
        "pct_positive_sharpe": round(float(np.mean(sim_sharpes > 0)) * 100, 1),
    }


def format_allocation(
    tickers: List[str],
    weights: List[float],
    short_names: Dict[str, str],
    min_weight: float = 0.01,
) -> List[Dict]:
    """Format allocation as human-readable position sizes.

    Returns sorted list of {stock, ticker, weight_pct, suggestion}.
    """
    allocations = []
    for ticker, w in zip(tickers, weights):
        short = short_names.get(ticker, ticker.replace(".KL", ""))
        pct = w * 100
        if pct < min_weight * 100:
            continue

        # Position size suggestion
        if pct >= 20:
            suggestion = "Core holding (≥20%)"
        elif pct >= 10:
            suggestion = "Major position (10-20%)"
        elif pct >= 5:
            suggestion = "Standard position (5-10%)"
        elif pct >= 2:
            suggestion = "Small position (2-5%)"
        else:
            suggestion = "Minimal position (<2%)"

        allocations.append({
            "stock": short,
            "ticker": ticker,
            "weight_pct": round(pct, 1),
            "suggestion": suggestion,
        })

    allocations.sort(key=lambda x: x["weight_pct"], reverse=True)
    return allocations


# ── Main ────────────────────────────────────────────────────────────

def run_monte_carlo(
    persona_id: Optional[str] = None,
    n_simulations: int = DEFAULT_SIMULATIONS,
    years: float = 2.0,
) -> Dict:
    """Run Monte Carlo for one or all personas.

    Returns:
        Dict with results per persona.
    """
    print(f"\n{'='*60}")
    print(f"Monte Carlo Position Sizing — {n_simulations} simulations × {years}yr data")
    print(f"{'='*60}")

    # Load available stocks
    all_stocks = get_all_stocks_dict()
    ticker_set = set(info["code"] for info in all_stocks.values())
    tickers = sorted(ticker_set)
    short_names = {info["code"]: short for short, info in all_stocks.items()}

    # Fetch returns
    returns_matrix, valid_tickers, mean_rets = fetch_returns(tickers, years)

    # Build ticker label index for short name mapping
    valid_short = {
        ticker: short_names.get(ticker, ticker.replace(".KL", ""))
        for ticker in valid_tickers
    }

    personas_to_run = [persona_id] if persona_id else ["ares", "demeter", "athena"]
    results = {}

    for pid in personas_to_run:
        limits = PERSONA_LIMITS.get(pid, {"max_single_position": 0.30, "min_stocks": 4})
        max_w = limits["max_single_position"]
        min_s = limits["min_stocks"]

        print(f"\n  [{pid.upper()}] Running {n_simulations} simulations "
              f"(max position: {max_w*100:.0f}%, min stocks: {min_s})...")

        mc = simulate_portfolios(
            returns_matrix,
            n_simulations=n_simulations,
            max_weight=max_w,
            min_stocks=min_s,
        )

        opt = mc["optimal_portfolio"]
        minvar = mc["min_variance_portfolio"]

        # Format allocations
        opt_alloc = format_allocation(valid_tickers, opt["weights"], valid_short)
        minvar_alloc = format_allocation(valid_tickers, minvar["weights"], valid_short)

        print(f"    Max Sharpe: {opt['sharpe_ratio']:.3f}  "
              f"Return: {opt['expected_return_pct']:+.1f}%  "
              f"Vol: {opt['volatility_pct']:.1f}%  "
              f"Stocks: {len(opt_alloc)}")
        print(f"    Min Var:    {minvar['sharpe_ratio']:.3f}  "
              f"Return: {minvar['expected_return_pct']:+.1f}%  "
              f"Vol: {minvar['volatility_pct']:.1f}%  "
              f"Stocks: {len(minvar_alloc)}")
        print(f"    Sharpe percentiles: P25={mc['sharpe_pctiles']['p25']:.3f}  "
              f"P50={mc['sharpe_pctiles']['p50']:.3f}  "
              f"P75={mc['sharpe_pctiles']['p75']:.3f}  "
              f"P90={mc['sharpe_pctiles']['p90']:.3f}")

        # Top 5 positions
        print(f"    Optimal allocation (top 5):")
        for a in opt_alloc[:5]:
            print(f"      {a['stock']:12s}  {a['weight_pct']:5.1f}%  — {a['suggestion']}")

        results[pid] = {
            "persona": pid,
            "constraints": {
                "max_single_position_pct": round(max_w * 100, 0),
                "min_stocks": min_s,
            },
            "optimal_portfolio": {
                **opt,
                "allocations": opt_alloc,
            },
            "min_variance_portfolio": {
                **minvar,
                "allocations": minvar_alloc,
            },
            "sharpe_distribution": {
                "pctiles": mc["sharpe_pctiles"],
                "mean": mc["mean_sharpe"],
                "pct_positive": mc["pct_positive_sharpe"],
            },
            "n_simulations": n_simulations,
            "n_stocks": len(valid_tickers),
            "data_years": years,
        }

    return results


def main():
    persona = None
    n_sims = DEFAULT_SIMULATIONS
    years = 2.0

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        arg = args[i]
        if arg.startswith("--persona="):
            persona = arg.split("=", 1)[1]
        elif arg == "--persona" and i + 1 < len(args):
            i += 1; persona = args[i]
        elif arg.startswith("--sims="):
            n_sims = int(arg.split("=", 1)[1])
        elif arg == "--sims" and i + 1 < len(args):
            i += 1; n_sims = int(args[i])
        elif arg.startswith("--years="):
            years = float(arg.split("=", 1)[1])
        elif arg == "--years" and i + 1 < len(args):
            i += 1; years = float(args[i])
        i += 1

    results = run_monte_carlo(persona_id=persona, n_simulations=n_sims, years=years)

    # Save results
    output_path = ROOT / "data" / "monte_carlo_allocations.json"
    output = {
        "generated_at": datetime.now(MALAYSIA_TZ).isoformat(),
        "n_simulations": n_sims,
        "years": years,
        "personas": results,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2))
    print(f"\n  ✓ Results saved to {output_path}")

    # Print summary comparison
    print(f"\n{'='*60}")
    print("Monte Carlo Summary — Optimal Portfolios:")
    print(f"{'='*60}")
    for pid, r in sorted(results.items(),
                          key=lambda x: x[1]["optimal_portfolio"]["sharpe_ratio"],
                          reverse=True):
        opt = r["optimal_portfolio"]
        marker = "👑" if pid == max(results, key=lambda p: results[p]["optimal_portfolio"]["sharpe_ratio"]) else "  "
        print(f"  {marker} {pid:8s}  Sharpe {opt['sharpe_ratio']:.3f}  "
              f"Return {opt['expected_return_pct']:+.1f}%  "
              f"Vol {opt['volatility_pct']:.1f}%  "
              f"Positions: {len(opt['allocations'])}")


if __name__ == "__main__":
    main()
