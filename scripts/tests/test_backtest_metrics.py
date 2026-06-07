"""Tests for backtest/metrics.py — CAGR, Sharpe, max drawdown, win rate, profit factor."""

import sys
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from backtest.metrics import (
    cagr,
    max_drawdown,
    sharpe_ratio,
    annualized_volatility,
    win_rate,
    profit_factor,
    total_return,
)


# ── cagr ───────────────────────────────────────────────────────────

def test_cagr_basic():
    """10% annual return over 3 years: 1000 → 1331."""
    result = cagr(1000, 1331, 3)
    assert abs(result - 0.10) < 0.001

def test_cagr_double_7_years():
    """Rule of 72: 10% over ~7.2 years doubles."""
    result = cagr(1000, 2000, 7.2)
    assert abs(result - 0.10) < 0.02

def test_cagr_zero_initial():
    """Zero initial → 0.0."""
    assert cagr(0, 1000, 1) == 0.0

def test_cagr_zero_years():
    """Zero years → 0.0."""
    assert cagr(1000, 2000, 0) == 0.0

def test_cagr_negative_final():
    """Negative final → 0.0."""
    assert cagr(1000, -500, 1) == 0.0

def test_cagr_flat_no_growth():
    """No change → 0% CAGR."""
    assert cagr(1000, 1000, 5) == 0.0

def test_cagr_fractional_year():
    """6 months: 1000 → 1050 → ~10.25% annualized."""
    result = cagr(1000, 1050, 0.5)
    # (1.05)^2 - 1 = 1.1025 - 1 = 0.1025
    assert abs(result - 0.1025) < 0.001


# ── max_drawdown ───────────────────────────────────────────────────

def test_max_drawdown_simple():
    """Peak 100 → 80 = -20%."""
    values = [100, 95, 80, 90, 85]
    assert abs(max_drawdown(values) - (-0.20)) < 0.001

def test_max_drawdown_multiple_peaks():
    """Two peaks, second drawdown worse."""
    values = [100, 90, 95, 80, 100, 70, 85]
    # Peak 100: dd to 80 = -20%, peak 100: dd to 70 = -30%
    assert abs(max_drawdown(values) - (-0.30)) < 0.001

def test_max_drawdown_always_rising():
    """No drawdown."""
    values = [100, 105, 110, 120]
    assert max_drawdown(values) == 0.0

def test_max_drawdown_always_falling():
    """Continuous decline from start."""
    values = [100, 90, 80, 70, 60]
    assert abs(max_drawdown(values) - (-0.40)) < 0.001

def test_max_drawdown_single_value():
    """One value → no drawdown."""
    assert max_drawdown([100]) == 0.0

def test_max_drawdown_empty():
    """Empty list → 0.0."""
    assert max_drawdown([]) == 0.0

def test_max_drawdown_flat():
    """Flat values → no drawdown."""
    assert max_drawdown([100, 100, 100]) == 0.0


# ── sharpe_ratio ───────────────────────────────────────────────────

def test_sharpe_positive():
    """Consistent positive returns → positive Sharpe."""
    rets = [0.001, 0.0012, 0.0008, 0.0011, 0.0009] * 50
    sr = sharpe_ratio(rets)
    assert sr > 0

def test_sharpe_zero_returns():
    """All zero returns → 0 Sharpe."""
    assert sharpe_ratio([0.0] * 100) == 0.0

def test_sharpe_insufficient_data():
    """Single return → 0.0."""
    assert sharpe_ratio([0.01]) == 0.0

def test_sharpe_negative():
    """All negative returns → negative Sharpe."""
    rets = [-0.001, -0.0012, -0.0008, -0.0011, -0.0009] * 50
    sr = sharpe_ratio(rets)
    assert sr < 0

def test_sharpe_high_risk_free():
    """Higher risk-free rate reduces Sharpe."""
    rets = [0.001, 0.0015, 0.0007, 0.0013, 0.0009] * 50
    sr_low = sharpe_ratio(rets, risk_free_annual=0.01)
    sr_high = sharpe_ratio(rets, risk_free_annual=0.10)
    assert sr_low > sr_high

def test_sharpe_mixed_returns():
    """Mixed returns give moderate Sharpe."""
    rets = [0.02, -0.01, 0.01, -0.005, 0.015] * 50
    sr = sharpe_ratio(rets)
    # With high returns and low variance, Sharpe can be high
    assert sr > 0  # positive overall


# ── annualized_volatility ──────────────────────────────────────────

def test_vol_constant_returns():
    """Constant daily returns → zero volatility."""
    assert annualized_volatility([0.001] * 100) == 0.0

def test_vol_simple():
    """Known variance."""
    rets = [0.01, -0.01, 0.01, -0.01] * 63  # ~252 days
    vol = annualized_volatility(rets)
    assert 0.15 < vol < 0.17  # ~16% ann from 1% daily swings

def test_vol_insufficient_data():
    """Single return → 0.0."""
    assert annualized_volatility([0.01]) == 0.0

def test_vol_high_variance():
    """Wide swings → high volatility."""
    rets = [0.05, -0.05] * 126
    vol = annualized_volatility(rets)
    assert vol > 0.5  # very high


# ── win_rate ────────────────────────────────────────────────────────

def test_win_rate_balanced():
    """3 wins, 2 losses → 60%."""
    trades = [
        {"pnl": 100}, {"pnl": 50}, {"pnl": -30}, {"pnl": 200}, {"pnl": -10}
    ]
    assert win_rate(trades) == 0.6

def test_win_rate_all_wins():
    """All profitable → 100%."""
    trades = [{"pnl": 100}, {"pnl": 50}]
    assert win_rate(trades) == 1.0

def test_win_rate_all_losses():
    """All losing → 0%."""
    trades = [{"pnl": -100}, {"pnl": -50}]
    assert win_rate(trades) == 0.0

def test_win_rate_empty():
    """No trades → 0.0."""
    assert win_rate([]) == 0.0

def test_win_rate_breakeven():
    """PnL of 0 counts as loss (not > 0)."""
    trades = [{"pnl": 0}, {"pnl": 100}]
    assert win_rate(trades) == 0.5

def test_win_rate_missing_pnl():
    """Missing pnl field treats as 0 → loss."""
    trades = [{"other": "data"}, {"pnl": 100}]
    assert win_rate(trades) == 0.5


# ── profit_factor ───────────────────────────────────────────────────

def test_profit_factor_basic():
    """Gross profit 300, gross loss 100 → PF = 3.0."""
    trades = [
        {"pnl": 100}, {"pnl": 200}, {"pnl": -50}, {"pnl": -50}
    ]
    assert profit_factor(trades) == 3.0

def test_profit_factor_no_losses():
    """No losses → inf."""
    trades = [{"pnl": 100}, {"pnl": 200}]
    assert profit_factor(trades) == float("inf")

def test_profit_factor_no_profits():
    """Only losses → 0.0."""
    trades = [{"pnl": -100}, {"pnl": -200}]
    assert profit_factor(trades) == 0.0

def test_profit_factor_empty():
    """No trades → 0.0."""
    assert profit_factor([]) == 0.0

def test_profit_factor_breakeven():
    """Equal profits and losses → PF = 1.0."""
    trades = [{"pnl": 100}, {"pnl": -100}]
    assert profit_factor(trades) == 1.0


# ── total_return ────────────────────────────────────────────────────

def test_total_return_gain():
    """1000 → 1200 = 20%."""
    assert total_return(1000, 1200) == 0.2

def test_total_return_loss():
    """1000 → 800 = -20%."""
    assert total_return(1000, 800) == -0.2

def test_total_return_zero_initial():
    """Zero initial → 0.0."""
    assert total_return(0, 1000) == 0.0

def test_total_return_no_change():
    """1000 → 1000 = 0%."""
    assert total_return(1000, 1000) == 0.0
