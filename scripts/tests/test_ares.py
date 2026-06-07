"""Tests for ares.py — trailing stop-loss strategy for Ares persona."""

import json
from unittest.mock import patch, mock_open
import sys
from pathlib import Path

# Add scripts/ to path so we can import strategies
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from strategies.ares import (
    check_trailing_stop,
    update_high_water_marks,
    get_peak_info,
    load_high_water_marks,
    TRAILING_STOP_PCT,
)


# --- Sample data ---

SAMPLE_HOLDINGS = {
    "MAYBANK": {"shares": 1000, "cost": 10.00},
    "PBBANK": {"shares": 2000, "cost": 4.50},
    "TENAGA": {"shares": 500, "cost": 14.00},
}

SAMPLE_PRICES = {
    "MAYBANK": 10.50,   # +5% from cost
    "PBBANK": 4.00,     # -11% from cost
    "TENAGA": 14.00,    # flat
}


def test_trailing_stop_triggers_at_15pct_drawdown():
    """Stop-loss fires when drawdown from peak reaches -15%."""
    high_water = {"MAYBANK": 12.00}  # peak was 12.00
    prices = {"MAYBANK": 10.20}      # now 10.20 = -15% from peak

    with patch("strategies.ares.load_high_water_marks", return_value={"ares": high_water}):
        trades = check_trailing_stop("ares", SAMPLE_HOLDINGS, prices)

    assert len(trades) == 1
    assert trades[0]["action"] == "SELL_ALL"
    assert trades[0]["stock"] == "MAYBANK"
    assert "Trailing stop" in trades[0]["reason"]
    assert "-15" in trades[0]["reason"]


def test_trailing_stop_does_not_trigger_at_10pct_drawdown():
    """Stop-loss does NOT fire at only -10% from peak."""
    high_water = {"MAYBANK": 12.00}
    prices = {"MAYBANK": 10.80}  # -10% from peak, not enough

    with patch("strategies.ares.load_high_water_marks", return_value={"ares": high_water}):
        trades = check_trailing_stop("ares", SAMPLE_HOLDINGS, prices)

    assert len(trades) == 0


def test_trailing_stop_exactly_at_threshold():
    """At exactly -15%, the stop should trigger (<= check)."""
    high_water = {"PBBANK": 5.00}
    prices = {"PBBANK": 4.25}  # -15% exactly

    holdings = {"PBBANK": {"shares": 2000, "cost": 4.50}}

    with patch("strategies.ares.load_high_water_marks", return_value={"ares": high_water}):
        trades = check_trailing_stop("ares", holdings, prices)

    assert len(trades) == 1
    assert trades[0]["stock"] == "PBBANK"


def test_trailing_stop_just_above_threshold_no_trigger():
    """At -14.9%, the stop should NOT trigger."""
    high_water = {"PBBANK": 5.00}
    prices = {"PBBANK": 4.255}  # -14.9%

    holdings = {"PBBANK": {"shares": 2000, "cost": 4.50}}

    with patch("strategies.ares.load_high_water_marks", return_value={"ares": high_water}):
        trades = check_trailing_stop("ares", holdings, prices)

    assert len(trades) == 0


def test_trailing_stop_price_at_peak_no_trigger():
    """When price equals peak, no drawdown → no trigger."""
    high_water = {"TENAGA": 14.00}
    prices = {"TENAGA": 14.00}

    holdings = {"TENAGA": {"shares": 500, "cost": 14.00}}

    with patch("strategies.ares.load_high_water_marks", return_value={"ares": high_water}):
        trades = check_trailing_stop("ares", holdings, prices)

    assert len(trades) == 0


def test_trailing_stop_price_above_peak_no_trigger():
    """When price above peak, no drawdown → no trigger."""
    high_water = {"MAYBANK": 10.00}
    prices = {"MAYBANK": 11.00}

    holdings = {"MAYBANK": {"shares": 1000, "cost": 10.00}}

    with patch("strategies.ares.load_high_water_marks", return_value={"ares": high_water}):
        trades = check_trailing_stop("ares", holdings, prices)

    assert len(trades) == 0


def test_trailing_stop_zero_price_skipped():
    """Zero or negative price should skip evaluation."""
    high_water = {"MAYBANK": 12.00}
    prices = {"MAYBANK": 0.0}

    holdings = {"MAYBANK": {"shares": 1000, "cost": 10.00}}

    with patch("strategies.ares.load_high_water_marks", return_value={"ares": high_water}):
        trades = check_trailing_stop("ares", holdings, prices)

    assert len(trades) == 0


def test_trailing_stop_no_high_water_uses_current_price():
    """If no high water mark exists, peak defaults to current price → no trigger."""
    # Empty marks
    with patch("strategies.ares.load_high_water_marks", return_value={}):
        trades = check_trailing_stop("ares", SAMPLE_HOLDINGS, SAMPLE_PRICES)

    assert len(trades) == 0


def test_trailing_stop_missing_price_uses_cost():
    """Missing price falls back to cost basis."""
    high_water = {"PBBANK": 5.00}
    # No PBBANK in prices dict → uses cost (4.50)
    prices = {}

    holdings = {"PBBANK": {"shares": 2000, "cost": 4.50}}

    with patch("strategies.ares.load_high_water_marks", return_value={"ares": high_water}):
        trades = check_trailing_stop("ares", holdings, prices)

    # drawdown = (4.50 - 5.00) / 5.00 = -10% → no trigger
    assert len(trades) == 0


def test_trailing_stop_multiple_positions():
    """Multiple positions — only breached ones trigger."""
    high_water = {
        "MAYBANK": 15.00,   # peak 15 → now 10.50 = -30% → TRIGGER
        "PBBANK": 4.20,     # peak 4.20 → now 4.00 = -4.8% → no trigger
        "TENAGA": 14.00,    # peak 14 → now 14 = 0% → no trigger
    }

    with patch("strategies.ares.load_high_water_marks", return_value={"ares": high_water}):
        trades = check_trailing_stop("ares", SAMPLE_HOLDINGS, SAMPLE_PRICES)

    assert len(trades) == 1
    assert trades[0]["stock"] == "MAYBANK"


def test_trailing_stop_uses_trade_reason_format():
    """Trade reason includes drawdown %, peak, and threshold."""
    high_water = {"MAYBANK": 12.00}
    prices = {"MAYBANK": 10.20}

    holdings = {"MAYBANK": {"shares": 1000, "cost": 10.00}}

    with patch("strategies.ares.load_high_water_marks", return_value={"ares": high_water}):
        trades = check_trailing_stop("ares", holdings, prices)

    assert len(trades) == 1
    reason = trades[0]["reason"]
    assert "Trailing stop" in reason
    assert "12.000" in reason  # peak price
    assert "15" in reason       # threshold %
    assert trades[0]["source"] == "trailing_stop"


def test_trailing_stop_returns_shares_and_price():
    """Trade dict includes shares and current price."""
    high_water = {"MAYBANK": 12.00}
    prices = {"MAYBANK": 10.20}

    holdings = {"MAYBANK": {"shares": 1000, "cost": 10.00}}

    with patch("strategies.ares.load_high_water_marks", return_value={"ares": high_water}):
        trades = check_trailing_stop("ares", holdings, prices)

    assert trades[0]["shares"] == 1000
    assert trades[0]["price"] == 10.20


def test_trailing_stop_custom_threshold():
    """Custom trailing_pct parameter overrides default 15%."""
    high_water = {"MAYBANK": 12.00}
    prices = {"MAYBANK": 10.75}  # -10.42% from peak (safely past 10% threshold)

    holdings = {"MAYBANK": {"shares": 1000, "cost": 10.00}}

    # With 10% threshold → triggers since -10.42% < -10%
    with patch("strategies.ares.load_high_water_marks", return_value={"ares": high_water}):
        trades = check_trailing_stop("ares", holdings, prices, trailing_pct=0.10)

    assert len(trades) == 1


def test_trailing_stop_default_pct_is_15():
    """Default trailing stop percentage is 0.15."""
    assert TRAILING_STOP_PCT == 0.15


# --- High water mark tests ---

def test_update_high_water_new_position():
    """New position initializes high water mark at current price."""
    with patch("strategies.ares.load_high_water_marks", return_value={}):
        with patch("strategies.ares.save_high_water_marks") as mock_save:
            marks = update_high_water_marks("ares", SAMPLE_HOLDINGS, SAMPLE_PRICES)

    assert "MAYBANK" in marks
    assert marks["MAYBANK"] == 10.50  # current price
    assert "PBBANK" in marks
    assert marks["PBBANK"] == 4.00
    mock_save.assert_called_once()


def test_update_high_water_raises_on_new_peak():
    """High water mark only goes UP when price exceeds previous peak."""
    existing = {"ares": {"MAYBANK": 10.00}}

    with patch("strategies.ares.load_high_water_marks", return_value=existing):
        with patch("strategies.ares.save_high_water_marks") as mock_save:
            marks = update_high_water_marks("ares", SAMPLE_HOLDINGS, SAMPLE_PRICES)

    # MAYBANK went from 10.00 to 10.50 → raise
    assert marks["MAYBANK"] == 10.50
    mock_save.assert_called_once()


def test_update_high_water_does_not_lower():
    """High water mark does NOT go down when price drops."""
    existing = {"ares": {"PBBANK": 5.00}}  # was higher

    with patch("strategies.ares.load_high_water_marks", return_value=existing):
        with patch("strategies.ares.save_high_water_marks") as mock_save:
            marks = update_high_water_marks("ares", SAMPLE_HOLDINGS, SAMPLE_PRICES)

    # PBBANK dropped from 5.00 to 4.00 — mark stays at 5.00
    assert marks["PBBANK"] == 5.00
    mock_save.assert_called_once()


def test_update_high_water_stays_same_when_equal():
    """High water mark unchanged when price equals previous peak."""
    existing = {"ares": {"TENAGA": 14.00}}

    with patch("strategies.ares.load_high_water_marks", return_value=existing):
        with patch("strategies.ares.save_high_water_marks") as mock_save:
            marks = update_high_water_marks("ares", SAMPLE_HOLDINGS, SAMPLE_PRICES)

    assert marks["TENAGA"] == 14.00
    mock_save.assert_called_once()


def test_update_high_water_zero_price_skipped():
    """Zero price does not create/update high water mark."""
    holdings = {"BADSTOCK": {"shares": 100, "cost": 1.00}}
    prices = {"BADSTOCK": 0.0}

    with patch("strategies.ares.load_high_water_marks", return_value={}):
        with patch("strategies.ares.save_high_water_marks") as mock_save:
            marks = update_high_water_marks("ares", holdings, prices)

    assert "BADSTOCK" not in marks
    mock_save.assert_called_once()


def test_update_high_water_missing_price_uses_cost():
    """Missing price falls back to cost for initialization."""
    holdings = {"ONLYCOST": {"shares": 100, "cost": 3.50}}
    prices = {}  # no price

    with patch("strategies.ares.load_high_water_marks", return_value={}):
        with patch("strategies.ares.save_high_water_marks") as mock_save:
            marks = update_high_water_marks("ares", holdings, prices)

    # Falls back to cost: 3.50
    assert marks.get("ONLYCOST") == 3.50


def test_update_high_water_multiple_portfolios_independent():
    """Each portfolio has independent high water marks."""
    existing = {
        "ares": {"MAYBANK": 12.00},
        "athena": {"MAYBANK": 11.00},
    }

    with patch("strategies.ares.load_high_water_marks", return_value=existing):
        with patch("strategies.ares.save_high_water_marks"):
            marks = update_high_water_marks("athena", SAMPLE_HOLDINGS, SAMPLE_PRICES)

    # Athena's MAYBANK mark stays at 11.00 (not affected by ares peak)
    assert marks["MAYBANK"] == 11.00


# --- get_peak_info tests ---

def test_get_peak_info_found():
    """Returns peak info for a tracked stock."""
    marks = {"ares": {"MAYBANK": 12.3456}}

    with patch("strategies.ares.load_high_water_marks", return_value=marks):
        info = get_peak_info("ares", "MAYBANK")

    assert info is not None
    assert info["peak_price"] == 12.3456
    assert info["trailing_stop_pct"] == 0.15


def test_get_peak_info_not_found():
    """Returns None for untracked stock."""
    with patch("strategies.ares.load_high_water_marks", return_value={}):
        info = get_peak_info("ares", "UNKNOWN")

    assert info is None


def test_get_peak_info_wrong_portfolio():
    """Returns None when stock is in a different portfolio."""
    marks = {"ares": {"MAYBANK": 10.00}}

    with patch("strategies.ares.load_high_water_marks", return_value=marks):
        info = get_peak_info("demeter", "MAYBANK")

    assert info is None


# --- load_high_water_marks tests ---

def test_load_high_water_marks_file_not_found():
    """Returns empty dict when file doesn't exist."""
    with patch("pathlib.Path.exists", return_value=False):
        marks = load_high_water_marks()
    assert marks == {}


def test_load_high_water_marks_corrupt_json():
    """Returns empty dict on JSON decode error."""
    with patch("pathlib.Path.exists", return_value=True):
        with patch("builtins.open", mock_open(read_data="not json")):
            marks = load_high_water_marks()
    assert marks == {}
