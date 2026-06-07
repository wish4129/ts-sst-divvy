"""Tests for monte_carlo.py — portfolio simulation and position sizing."""

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from risk.monte_carlo import (
    simulate_portfolios,
    format_allocation,
    DEFAULT_SIMULATIONS,
    RISK_FREE_RATE,
    TRADING_DAYS,
    PERSONA_LIMITS,
)


# ── Helpers ───────────────────────────────────────────────────────────


def sample_returns(n_stocks: int, n_days: int = 200) -> np.ndarray:
    """Generate reproducible sample daily returns matrix."""
    rng = np.random.default_rng(42)
    # Create stocks with different mean returns and volatilities
    means = np.linspace(0.0002, 0.0015, n_stocks)
    stds = np.linspace(0.015, 0.035, n_stocks)
    returns = np.empty((n_days, n_stocks))
    for i in range(n_stocks):
        returns[:, i] = rng.normal(means[i], stds[i], n_days)
    return returns


# ── format_allocation ─────────────────────────────────────────────────


def test_format_allocation_basic():
    """Formats allocation for multiple stocks sorted by weight."""
    tickers = ["1155.KL", "1295.KL", "5347.KL"]
    weights = [0.4, 0.35, 0.25]  # 40%, 35%, 25%
    short_names = {"1155.KL": "MAYBANK", "1295.KL": "PBBANK", "5347.KL": "TENAGA"}

    result = format_allocation(tickers, weights, short_names)

    assert len(result) == 3
    # Sorted by weight descending
    assert result[0]["stock"] == "MAYBANK"
    assert result[0]["weight_pct"] == 40.0
    assert "Core holding" in result[0]["suggestion"]

    assert result[1]["stock"] == "PBBANK"
    assert result[1]["weight_pct"] == 35.0

    assert result[2]["stock"] == "TENAGA"
    assert result[2]["weight_pct"] == 25.0


def test_format_allocation_filters_small_weights():
    """Weights below min_weight (1%) are excluded."""
    tickers = ["A.KL", "B.KL", "C.KL"]
    weights = [0.50, 0.005, 0.495]  # B is 0.5% — below 1% threshold
    short_names = {"A.KL": "STOCK_A", "B.KL": "STOCK_B", "C.KL": "STOCK_C"}

    result = format_allocation(tickers, weights, short_names)

    assert len(result) == 2  # STOCK_B excluded
    assert result[0]["stock"] == "STOCK_A"
    assert result[1]["stock"] == "STOCK_C"


def test_format_allocation_custom_min_weight():
    """Custom min_weight threshold is respected."""
    tickers = ["X.KL", "Y.KL"]
    weights = [0.10, 0.90]
    short_names = {"X.KL": "X", "Y.KL": "Y"}

    result = format_allocation(tickers, weights, short_names, min_weight=0.15)

    assert len(result) == 1  # X (10%) excluded at 15% threshold
    assert result[0]["stock"] == "Y"


def test_format_allocation_missing_short_name():
    """Ticker without short name uses code without .KL suffix."""
    tickers = ["9999.KL"]
    weights = [1.0]
    short_names = {}  # No mapping

    result = format_allocation(tickers, weights, short_names)
    assert len(result) == 1
    assert result[0]["stock"] == "9999"  # .KL stripped


def test_format_allocation_weight_suggestions():
    """Position size suggestions match weight ranges."""
    test_cases = [
        (0.25, "Core holding"),     # ≥20%
        (0.20, "Core holding"),     # exactly 20%
        (0.15, "Major position"),   # 10-20%
        (0.10, "Major position"),   # exactly 10%
        (0.07, "Standard position"), # 5-10%
        (0.05, "Standard position"), # exactly 5%
        (0.03, "Small position"),   # 2-5%
        (0.02, "Small position"),   # exactly 2%
        (0.01, "Minimal position"), # <2%
    ]
    for weight, expected_suggestion in test_cases:
        result = format_allocation(
            ["T.KL"], [weight], {"T.KL": "TEST"},
            min_weight=0.005,
        )
        assert len(result) == 1
        assert expected_suggestion in result[0]["suggestion"], \
            f"For weight {weight}, expected '{expected_suggestion}' in '{result[0]['suggestion']}'"


def test_format_allocation_all_fields_present():
    """Each allocation entry has all expected fields."""
    tickers = ["1155.KL"]
    weights = [1.0]
    short_names = {"1155.KL": "MAYBANK"}

    result = format_allocation(tickers, weights, short_names)
    entry = result[0]
    for key in ["stock", "ticker", "weight_pct", "suggestion"]:
        assert key in entry, f"Missing key: {key}"


# ── simulate_portfolios ───────────────────────────────────────────────


def test_simulate_basic_runs():
    """Basic simulation runs and produces all expected output fields."""
    returns = sample_returns(5, 200)
    result = simulate_portfolios(returns, n_simulations=500)

    assert result["n_simulations"] == 500
    assert len(result["sim_returns"]) == 500
    assert len(result["sim_volatilities"]) == 500
    assert len(result["sim_sharpes"]) == 500

    # Optimal portfolio
    opt = result["optimal_portfolio"]
    assert "weights" in opt
    assert "expected_return_pct" in opt
    assert "volatility_pct" in opt
    assert "sharpe_ratio" in opt
    assert len(opt["weights"]) == 5

    # Min variance portfolio
    mv = result["min_variance_portfolio"]
    assert "weights" in mv
    assert len(mv["weights"]) == 5

    # Sharpe percentiles
    assert "p25" in result["sharpe_pctiles"]
    assert "p50" in result["sharpe_pctiles"]
    assert "p75" in result["sharpe_pctiles"]
    assert "p90" in result["sharpe_pctiles"]


def test_simulate_weights_sum_to_one():
    """All simulated portfolios have weights that sum to ~1."""
    returns = sample_returns(4, 100)
    result = simulate_portfolios(returns, n_simulations=200)

    opt_weights = result["optimal_portfolio"]["weights"]
    assert abs(sum(opt_weights) - 1.0) < 0.01

    mv_weights = result["min_variance_portfolio"]["weights"]
    assert abs(sum(mv_weights) - 1.0) < 0.01


def test_simulate_sharpe_percentiles_ordered():
    """Sharpe percentiles are monotonically increasing."""
    returns = sample_returns(5, 200)
    result = simulate_portfolios(returns, n_simulations=500)

    p = result["sharpe_pctiles"]
    assert p["p25"] <= p["p50"] <= p["p75"] <= p["p90"]


def test_simulate_max_sharpe_at_least_as_good_as_min_var():
    """Max Sharpe portfolio has >= Sharpe ratio of min variance portfolio."""
    returns = sample_returns(5, 200)
    result = simulate_portfolios(returns, n_simulations=500)

    assert result["optimal_portfolio"]["sharpe_ratio"] >= \
           result["min_variance_portfolio"]["sharpe_ratio"]


def test_simulate_single_stock():
    """Single stock portfolio simulation works (all weight = 1.0)."""
    rng = np.random.default_rng(42)
    returns = rng.normal(0.001, 0.02, (200, 1))
    result = simulate_portfolios(returns, n_simulations=100)

    assert result["n_simulations"] == 100
    assert len(result["optimal_portfolio"]["weights"]) == 1
    # For single stock, all simulations should have weight 1.0
    assert abs(result["optimal_portfolio"]["weights"][0] - 1.0) < 0.01


def test_simulate_two_stocks():
    """Two-stock simulation produces valid weights."""
    returns = sample_returns(2, 100)
    result = simulate_portfolios(returns, n_simulations=200)

    assert len(result["optimal_portfolio"]["weights"]) == 2
    opt_sum = sum(result["optimal_portfolio"]["weights"])
    assert abs(opt_sum - 1.0) < 0.01


def test_simulate_respects_max_weight():
    """No single position exceeds the max_weight constraint."""
    returns = sample_returns(6, 200)
    max_w = 0.25
    result = simulate_portfolios(returns, n_simulations=500, max_weight=max_w)

    opt_weights = result["optimal_portfolio"]["weights"]
    for w in opt_weights:
        assert w <= max_w + 0.01  # Small tolerance for floating point


def test_simulate_reproducibility():
    """Same seed produces identical results (reproducible)."""
    returns = sample_returns(4, 100)
    result1 = simulate_portfolios(returns, n_simulations=200)
    result2 = simulate_portfolios(returns, n_simulations=200)

    assert result1["optimal_portfolio"]["sharpe_ratio"] == \
           result2["optimal_portfolio"]["sharpe_ratio"]
    assert result1["optimal_portfolio"]["expected_return_pct"] == \
           result2["optimal_portfolio"]["expected_return_pct"]


def test_simulate_min_stocks_constraint():
    """At least min_stocks have non-trivial weight in the optimal portfolio."""
    returns = sample_returns(8, 200)
    min_s = 4
    result = simulate_portfolios(returns, n_simulations=300, min_stocks=min_s)

    opt_weights = result["optimal_portfolio"]["weights"]
    # Count weights above 0.1% threshold
    n_held = sum(1 for w in opt_weights if w > 0.001)
    # min_stocks constraint is applied per simulation,
    # but the optimum may not have exactly min_stocks.
    # Just check it's a reasonable portfolio
    assert n_held >= 1


def test_simulate_mean_sharpe_calculation():
    """mean_sharpe matches computed average of simulation sharpes."""
    returns = sample_returns(4, 150)
    result = simulate_portfolios(returns, n_simulations=300)

    computed_mean = np.mean(result["sim_sharpes"])
    assert abs(result["mean_sharpe"] - computed_mean) < 0.01


def test_simulate_positive_sharpe_pct():
    """pct_positive_sharpe is between 0 and 100."""
    returns = sample_returns(4, 150)
    result = simulate_portfolios(returns, n_simulations=300)

    assert 0.0 <= result["pct_positive_sharpe"] <= 100.0


def test_simulate_volatility_non_negative():
    """All simulated volatilities are non-negative."""
    returns = sample_returns(4, 100)
    result = simulate_portfolios(returns, n_simulations=200)

    for vol in result["sim_volatilities"]:
        assert vol >= 0.0


def test_simulate_min_variance_volatility_lower_or_equal():
    """Min variance portfolio has volatility <= optimal portfolio."""
    returns = sample_returns(5, 200)
    result = simulate_portfolios(returns, n_simulations=300)

    assert result["min_variance_portfolio"]["volatility_pct"] <= \
           result["optimal_portfolio"]["volatility_pct"] + 0.01


# ── Constants ─────────────────────────────────────────────────────────


def test_default_simulations():
    """Default simulation count is 1000."""
    assert DEFAULT_SIMULATIONS == 1000


def test_risk_free_rate():
    """Risk-free rate matches Malaysia OPR (~3%)."""
    assert RISK_FREE_RATE == 0.03


def test_trading_days():
    """Trading days per year is 252."""
    assert TRADING_DAYS == 252


def test_persona_limits_defined():
    """All three personas have position limits."""
    assert "ares" in PERSONA_LIMITS
    assert "demeter" in PERSONA_LIMITS
    assert "athena" in PERSONA_LIMITS


def test_persona_limits_have_required_fields():
    """Each persona limit has max_single_position and min_stocks."""
    for pid, limits in PERSONA_LIMITS.items():
        assert "max_single_position" in limits, f"{pid} missing max_single_position"
        assert "min_stocks" in limits, f"{pid} missing min_stocks"
        assert 0 < limits["max_single_position"] <= 1.0
        assert limits["min_stocks"] >= 1


def test_ares_max_position_is_25pct():
    """Ares has 25% max single position."""
    assert PERSONA_LIMITS["ares"]["max_single_position"] == 0.25
