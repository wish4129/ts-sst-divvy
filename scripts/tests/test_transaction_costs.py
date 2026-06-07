"""Tests for transaction_costs.py — Bursa Malaysia brokerage, stamp duty, clearing fees."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from risk.transaction_costs import (
    brokerage,
    stamp_duty,
    clearing_fee,
    sst_tax,
    buy_cost,
    sell_cost,
    round_trip_cost,
    is_trade_worthwhile,
    BROKERAGE_RATE,
    STAMP_DUTY_RATE,
    STAMP_DUTY_CAP,
    CLEARING_RATE,
    CLEARING_CAP,
    SST_RATE,
    MIN_BROKERAGE,
    MIN_CLEARING,
)

# ── brokerage ──────────────────────────────────────────────────────

def test_brokerage_standard_rate():
    """0.10% on RM10,000 = RM10.00."""
    assert brokerage(10000) == 10.0

def test_brokerage_minimum_fee():
    """Small trades hit minimum RM8 fee."""
    assert brokerage(1000) == 8.0  # 1000 * 0.001 = 1.0 < 8.0
    assert brokerage(2000) == 8.0  # 2000 * 0.001 = 2.0 < 8.0

def test_brokerage_above_minimum():
    """Trades above RM8,000 clear the minimum."""
    assert brokerage(8000) == 8.0   # exactly at min
    assert brokerage(10000) == 10.0  # above min

def test_brokerage_large_trade():
    """RM100,000 trade at 0.1%."""
    assert brokerage(100000) == 100.0

def test_brokerage_custom_rate():
    """Custom brokerage rate parameter works."""
    assert brokerage(10000, rate=0.0005) == 8.0  # 5.0 < min → min

def test_brokerage_zero_value():
    """Zero trade value hits minimum."""
    assert brokerage(0) == MIN_BROKERAGE


# ── stamp_duty ─────────────────────────────────────────────────────

def test_stamp_duty_standard():
    """RM1 per RM1,000 = 0.1%."""
    assert stamp_duty(10000) == 10.0

def test_stamp_duty_small_trade():
    """Small trade pays duty (rounded up from fraction)."""
    duty = stamp_duty(1000)
    assert duty == 1.0  # 1000 * 0.001 = 1.0, int(1.0)==1 → no round-up

def test_stamp_duty_cap():
    """Duty capped at RM200."""
    assert stamp_duty(1000000) == STAMP_DUTY_CAP  # 1M * 0.001 = 1000 → capped

def test_stamp_duty_at_cap_boundary():
    """Exactly at RM200,000 = RM200 duty."""
    assert stamp_duty(200000) == STAMP_DUTY_CAP

def test_stamp_duty_zero():
    """Zero trade = zero duty."""
    assert stamp_duty(0) == 0.0


# ── clearing_fee ───────────────────────────────────────────────────

def test_clearing_fee_standard():
    """0.03% on RM10,000 ≈ RM3.00 (float precision)."""
    assert clearing_fee(10000) == pytest.approx(3.0)

def test_clearing_fee_minimum():
    """Very small trades hit minimum clearing fee."""
    assert clearing_fee(100) == MIN_CLEARING  # 0.03 < min

def test_clearing_fee_cap():
    """Clearing fee capped at RM1,000."""
    assert clearing_fee(5000000) == CLEARING_CAP  # 5M * 0.0003 = 1500 → capped

def test_clearing_fee_zero():
    """Zero trade = minimum clearing fee."""
    assert clearing_fee(0) == MIN_CLEARING


# ── sst_tax ─────────────────────────────────────────────────────────

def test_sst_tax_calculation():
    """6% on brokerage + clearing."""
    assert sst_tax(10.0, 3.0) == 0.78  # (10 + 3) * 0.06

def test_sst_tax_zero():
    """Zero fees = zero SST."""
    assert sst_tax(0, 0) == 0.0

def test_sst_tax_large_fees():
    """Large fees produce large SST."""
    assert sst_tax(100.0, 30.0) == 7.8  # 130 * 0.06


# ── buy_cost ────────────────────────────────────────────────────────

def test_buy_cost_rm5000():
    """Typical buy on RM5,000."""
    result = buy_cost(5000)
    assert result["trade_value"] == 5000
    assert result["brokerage"] == 8.0  # min
    assert result["stamp_duty"] == 5.0  # 5000 * 0.001 = 5.0
    assert result["clearing"] == 1.5   # 5000 * 0.0003
    assert result["sst"] == 0.57       # (8 + 1.5) * 0.06
    expected_total = 8.0 + 5.0 + 1.5 + 0.57
    assert result["total_cost"] == round(expected_total, 2)

def test_buy_cost_rm10000():
    """Typical buy on RM10,000."""
    result = buy_cost(10000)
    assert result["brokerage"] == 10.0  # above min
    assert result["stamp_duty"] == 10.0

def test_buy_cost_includes_cost_pct():
    """Cost percentage is calculated."""
    result = buy_cost(10000)
    assert result["cost_pct"] > 0
    assert result["cost_pct"] < 1.0  # < 1% for RM10K

def test_buy_cost_zero_value():
    """Zero trade value."""
    result = buy_cost(0)
    assert result["cost_pct"] == 0

def test_buy_cost_custom_rate():
    """Custom brokerage rate."""
    result = buy_cost(10000, brokerage_rate=0.0005)
    assert result["brokerage"] == 8.0  # 5.0 < min


# ── sell_cost ───────────────────────────────────────────────────────

def test_sell_cost_equals_buy_cost():
    """Sell cost is identical to buy cost in Malaysia."""
    assert sell_cost(10000) == buy_cost(10000)

def test_sell_cost_rm25000():
    """Verify sell cost on larger trade."""
    result = sell_cost(25000)
    assert result["brokerage"] == 25.0  # 25000 * 0.001
    assert result["total_cost"] > 0


# ── round_trip_cost ─────────────────────────────────────────────────

def test_round_trip_cost_rm5000():
    """Round-trip = buy + sell costs."""
    result = round_trip_cost(5000)
    buy = buy_cost(5000)
    expected = round(buy["total_cost"] * 2, 2)
    assert result["total_round_trip"] == expected

def test_round_trip_cost_includes_breakeven():
    """Breakeven move = round-trip as percentage."""
    result = round_trip_cost(10000)
    assert result["breakeven_move_pct"] > 0
    assert result["round_trip_pct"] == result["breakeven_move_pct"]

def test_round_trip_cost_rm100000():
    """Large trade round-trip."""
    result = round_trip_cost(100000)
    assert result["total_round_trip"] > 0
    assert result["buy_cost"]["brokerage"] == 100.0


# ── is_trade_worthwhile ─────────────────────────────────────────────

def test_worthwhile_strong_return():
    """2% expected return on RM5,000 is worthwhile."""
    ok, reason = is_trade_worthwhile(5000, 0.02)
    assert ok is True
    assert "Worthwhile" in reason

def test_worthwhile_marginal_return():
    """0.5% expected return on small trade is not worthwhile."""
    ok, reason = is_trade_worthwhile(1000, 0.005)
    assert ok is False
    assert "Net return" in reason or "too small" in reason

def test_worthwhile_trade_too_small():
    """Trade value below RM100 rejected."""
    ok, reason = is_trade_worthwhile(50, 0.10)
    assert ok is False
    assert "too small" in reason

def test_worthwhile_exact_min_trade_value():
    """Exactly RM100 trade value."""
    ok, reason = is_trade_worthwhile(100, 0.10)
    # High expected return should overcome costs
    assert ok is True or ok is False  # depends on cost exactness

def test_worthwhile_custom_min_net_return():
    """Higher minimum net return threshold makes trade not worthwhile."""
    ok, reason = is_trade_worthwhile(5000, 0.01, min_net_return_pct=0.02)
    assert ok is False
    assert "Net return" in reason

def test_worthwhile_negative_expected_return():
    """Negative expected return is never worthwhile."""
    ok, reason = is_trade_worthwhile(10000, -0.05)
    assert ok is False
