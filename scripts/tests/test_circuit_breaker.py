"""Tests for circuit_breaker.py — max drawdown detection and buy blocking."""

import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from risk.circuit_breaker import (
    _load_state,
    _save_state,
    get_peak_value,
    update_peak,
    check_circuit_breaker,
    is_buy_blocked,
    get_circuit_breaker_summary,
    DEFAULT_THRESHOLD,
    PERSONA_THRESHOLDS,
)

# ── _load_state / _save_state ──────────────────────────────────────────


def test_load_state_no_file_returns_empty():
    """When state file doesn't exist, return default empty dict."""
    with patch("risk.circuit_breaker.STATE_PATH") as mock_path:
        mock_path.exists.return_value = False
        state = _load_state()
    assert state == {"personas": {}}


def test_load_state_valid_returns_parsed():
    """Valid JSON is loaded correctly."""
    data = {"personas": {"ares": {"peak_value": 10500.0}}}
    with patch("risk.circuit_breaker.STATE_PATH") as mock_path:
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = json.dumps(data)
        state = _load_state()
    assert state["personas"]["ares"]["peak_value"] == 10500.0


def test_load_state_corrupted_json_returns_empty():
    """Corrupted JSON returns default empty dict."""
    with patch("risk.circuit_breaker.STATE_PATH") as mock_path:
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = "{bad json"
        state = _load_state()
    assert state == {"personas": {}}


def test_save_state_writes_json():
    """State is persisted as formatted JSON."""
    state = {"personas": {"demeter": {"peak_value": 9800.0}}}
    with patch("risk.circuit_breaker.STATE_PATH") as mock_path:
        _save_state(state)
    assert mock_path.parent.mkdir.called
    mock_path.write_text.assert_called_once()
    written = mock_path.write_text.call_args[0][0]
    assert "9800.0" in written


# ── get_peak_value ────────────────────────────────────────────────────


def test_get_peak_value_returns_peak():
    """Returns stored peak value for a persona."""
    data = {"personas": {"athena": {"peak_value": 10200.0}}}
    with patch("risk.circuit_breaker._load_state", return_value=data):
        peak = get_peak_value("athena")
    assert peak == 10200.0


def test_get_peak_value_unknown_persona_returns_none():
    """Unknown persona returns None."""
    with patch("risk.circuit_breaker._load_state", return_value={"personas": {}}):
        peak = get_peak_value("unknown")
    assert peak is None


def test_get_peak_value_no_peak_set_returns_none():
    """Persona exists but no peak recorded yet."""
    data = {"personas": {"ares": {}}}
    with patch("risk.circuit_breaker._load_state", return_value=data):
        peak = get_peak_value("ares")
    assert peak is None


# ── update_peak ───────────────────────────────────────────────────────


def test_update_peak_new_high():
    """Peak updates when current value exceeds stored peak."""
    data = {"personas": {"ares": {"peak_value": 10000.0}}}
    with patch("risk.circuit_breaker._load_state", return_value=data), \
         patch("risk.circuit_breaker._save_state") as mock_save:
        peak = update_peak("ares", 10500.0)
    assert peak == 10500.0
    assert mock_save.called


def test_update_peak_below_peak_no_change():
    """Peak stays when current value is below stored peak."""
    data = {"personas": {"demeter": {"peak_value": 10100.0}}}
    with patch("risk.circuit_breaker._load_state", return_value=data), \
         patch("risk.circuit_breaker._save_state") as mock_save:
        peak = update_peak("demeter", 9800.0)
    assert peak == 10100.0
    assert mock_save.called


def test_update_peak_first_run_sets_peak():
    """On first run (no existing peak), sets current as peak."""
    with patch("risk.circuit_breaker._load_state", return_value={"personas": {}}), \
         patch("risk.circuit_breaker._save_state") as mock_save:
        peak = update_peak("athena", 10000.0)
    assert peak == 10000.0
    assert mock_save.called


def test_update_peak_equal_to_peak_keeps():
    """When current equals peak, no change needed."""
    data = {"personas": {"ares": {"peak_value": 10000.0}}}
    with patch("risk.circuit_breaker._load_state", return_value=data), \
         patch("risk.circuit_breaker._save_state") as mock_save:
        peak = update_peak("ares", 10000.0)
    assert peak == 10000.0
    assert mock_save.called


# ── check_circuit_breaker ─────────────────────────────────────────────


def test_check_cb_not_tripped_at_small_drawdown():
    """Circuit breaker does NOT trip at -10% (below 25% threshold)."""
    data = {"personas": {"ares": {"peak_value": 10000.0}}}
    with patch("risk.circuit_breaker._load_state", return_value=data), \
         patch("risk.circuit_breaker._save_state"):
        tripped, dd, state = check_circuit_breaker("ares", 9000.0)
    assert tripped is False
    assert dd == -0.1


def test_check_cb_trips_at_threshold():
    """Circuit breaker trips at exactly -25% (ares default)."""
    data = {"personas": {"ares": {"peak_value": 10000.0}}}
    with patch("risk.circuit_breaker._load_state", return_value=data), \
         patch("risk.circuit_breaker._save_state"):
        tripped, dd, state = check_circuit_breaker("ares", 7500.0)
    assert tripped is True
    assert abs(dd + 0.25) < 0.0001


def test_check_cb_trips_below_threshold():
    """Circuit breaker trips at -30% (below 25% threshold)."""
    data = {"personas": {"ares": {"peak_value": 10000.0}}}
    with patch("risk.circuit_breaker._load_state", return_value=data), \
         patch("risk.circuit_breaker._save_state"):
        tripped, dd, state = check_circuit_breaker("ares", 7000.0)
    assert tripped is True
    assert dd == -0.3


def test_check_cb_demeter_lower_threshold():
    """Demeter trips at -20% (more conservative threshold)."""
    data = {"personas": {"demeter": {"peak_value": 10000.0}}}
    with patch("risk.circuit_breaker._load_state", return_value=data), \
         patch("risk.circuit_breaker._save_state"):
        tripped, dd, state = check_circuit_breaker("demeter", 7900.0)
    assert tripped is True  # -21% > 20% threshold


def test_check_cb_zero_peak_no_trip():
    """When peak is zero or negative, no trip possible."""
    data = {"personas": {"ares": {"peak_value": 0.0}}}
    with patch("risk.circuit_breaker._load_state", return_value=data), \
         patch("risk.circuit_breaker._save_state"):
        tripped, dd, state = check_circuit_breaker("ares", 5000.0)
    assert tripped is False
    assert dd == 0.0


def test_check_cb_zero_current_no_trip():
    """When current value is zero, no trip (avoids division issues)."""
    data = {"personas": {"ares": {"peak_value": 10000.0}}}
    with patch("risk.circuit_breaker._load_state", return_value=data), \
         patch("risk.circuit_breaker._save_state"):
        tripped, dd, state = check_circuit_breaker("ares", 0.0)
    assert tripped is False
    assert dd == 0.0


def test_check_cb_recovers_after_trip():
    """When value recovers above threshold, trip is cleared."""
    data = {"personas": {
        "ares": {"peak_value": 10000.0, "tripped": True, "tripped_count": 1}
    }}
    with patch("risk.circuit_breaker._load_state", return_value=data), \
         patch("risk.circuit_breaker._save_state"):
        tripped, dd, state = check_circuit_breaker("ares", 8500.0)
    assert tripped is False


def test_check_cb_custom_threshold():
    """Custom threshold overrides persona default."""
    data = {"personas": {"ares": {"peak_value": 10000.0}}}
    with patch("risk.circuit_breaker._load_state", return_value=data), \
         patch("risk.circuit_breaker._save_state"):
        tripped, dd, state = check_circuit_breaker("ares", 8500.0, threshold=0.10)
    assert tripped is True  # -15% > 10% custom threshold


def test_check_cb_records_trip_count():
    """Trip count increments on each new trip."""
    data = {"personas": {"athena": {"peak_value": 10000.0}}}
    with patch("risk.circuit_breaker._load_state", return_value=data), \
         patch("risk.circuit_breaker._save_state") as mock_save:
        check_circuit_breaker("athena", 7500.0)  # -25% triggers athena's 22%
    saved_state = mock_save.call_args[0][0]
    pid_state = saved_state["personas"]["athena"]
    assert pid_state["tripped"] is True
    assert pid_state["tripped_count"] == 1


def test_check_cb_just_above_threshold_no_trip():
    """Just above threshold does not trip."""
    # ares threshold = 25% → -24.9% should NOT trip
    data = {"personas": {"ares": {"peak_value": 10000.0}}}
    with patch("risk.circuit_breaker._load_state", return_value=data), \
         patch("risk.circuit_breaker._save_state"):
        tripped, dd, state = check_circuit_breaker("ares", 7510.0)
    assert tripped is False  # -24.9%, below threshold


# ── is_buy_blocked ────────────────────────────────────────────────────


def test_is_buy_blocked_when_tripped():
    """Buy orders blocked when circuit breaker tripped."""
    data = {"personas": {"demeter": {"peak_value": 10000.0}}}
    with patch("risk.circuit_breaker._load_state", return_value=data), \
         patch("risk.circuit_breaker._save_state"):
        blocked, reason = is_buy_blocked("demeter", 7800.0)
    assert blocked is True
    assert "TRIPPED" in reason
    assert "SELL" in reason


def test_is_buy_blocked_when_ok():
    """Buy orders allowed when circuit breaker not tripped."""
    data = {"personas": {"ares": {"peak_value": 10000.0}}}
    with patch("risk.circuit_breaker._load_state", return_value=data), \
         patch("risk.circuit_breaker._save_state"):
        blocked, reason = is_buy_blocked("ares", 9500.0)
    assert blocked is False
    assert reason == ""


# ── get_circuit_breaker_summary ───────────────────────────────────────


def test_summary_ok():
    """OK status when drawdown is small."""
    data = {"personas": {"ares": {
        "peak_value": 10000.0, "tripped": False,
        "current_drawdown": -0.05, "tripped_count": 0,
    }}}
    with patch("risk.circuit_breaker._load_state", return_value=data):
        summary = get_circuit_breaker_summary("ares")
    assert summary["status"] == "🟢 OK"
    assert summary["tripped"] is False


def test_summary_warning():
    """WARNING when drawdown is within 50% of threshold."""
    # ares threshold=25%, drawdown -15% > 12.5% (50% of threshold)
    data = {"personas": {"ares": {
        "peak_value": 10000.0, "tripped": False,
        "current_drawdown": -0.15, "tripped_count": 0,
    }}}
    with patch("risk.circuit_breaker._load_state", return_value=data):
        summary = get_circuit_breaker_summary("ares")
    assert summary["status"] == "🟡 WARNING"
    assert summary["tripped"] is False


def test_summary_tripped():
    """TRIPPED when breaker is active."""
    data = {"personas": {"demeter": {
        "peak_value": 10000.0, "tripped": True,
        "current_drawdown": -0.22, "tripped_count": 2,
        "tripped_at": "2026-01-01T00:00:00+08:00",
    }}}
    with patch("risk.circuit_breaker._load_state", return_value=data):
        summary = get_circuit_breaker_summary("demeter")
    assert summary["status"] == "🔴 TRIPPED"
    assert summary["trip_count"] == 2


def test_summary_unknown_persona():
    """Unknown persona returns sensible defaults."""
    with patch("risk.circuit_breaker._load_state", return_value={"personas": {}}):
        summary = get_circuit_breaker_summary("unknown")
    assert summary["peak_value"] is None
    assert summary["trip_count"] == 0


def test_summary_fields_all_present():
    """All expected fields are in the summary dict."""
    data = {"personas": {"ares": {
        "peak_value": 10500.0, "tripped": False,
        "current_drawdown": -0.03, "tripped_count": 0,
        "tripped_at": None, "recovered_at": None, "peak_date": "2026-06-01",
    }}}
    with patch("risk.circuit_breaker._load_state", return_value=data):
        summary = get_circuit_breaker_summary("ares")
    for key in ["persona", "status", "tripped", "peak_value",
                "current_drawdown_pct", "threshold_pct", "trip_count",
                "tripped_at", "recovered_at", "peak_date"]:
        assert key in summary, f"Missing key: {key}"


# ── DEFAULT_THRESHOLD and PERSONA_THRESHOLDS ──────────────────────────


def test_default_threshold_is_25pct():
    """Default threshold is 0.25 (25%)."""
    assert DEFAULT_THRESHOLD == 0.25


def test_persona_thresholds_defined():
    """All three personas have threshold definitions."""
    assert "ares" in PERSONA_THRESHOLDS
    assert "demeter" in PERSONA_THRESHOLDS
    assert "athena" in PERSONA_THRESHOLDS


def test_demeter_threshold_lowest():
    """Demeter has the most conservative (lowest) threshold."""
    assert PERSONA_THRESHOLDS["demeter"] <= PERSONA_THRESHOLDS["ares"]
    assert PERSONA_THRESHOLDS["demeter"] <= PERSONA_THRESHOLDS["athena"]
