"""Tests for strategy modules: ares trailing stop, RSI, volume confirmation."""

import sys
from pathlib import Path

# Ensure scripts/ is importable
ROOT = Path(__file__).resolve().parent.parent.parent  # scripts/tests/../../ = divvy/
sys.path.insert(0, str(ROOT / "scripts"))


class TestAresTrailingStop:
    """Tests for scripts/strategies/ares.py."""

    def test_check_trailing_stop_no_drawdown(self, tmp_path, monkeypatch):
        """No trades when price hasn't dropped below threshold."""
        from strategies.ares import check_trailing_stop, HIGH_WATER_PATH

        monkeypatch.setattr("strategies.ares.HIGH_WATER_PATH", tmp_path / "hwm.json")

        holdings = {"MAYBANK": {"shares": 1000, "cost": 10.00}}
        prices = {"MAYBANK": 10.50}
        trades = check_trailing_stop("ares", holdings, prices)
        assert trades == []

    def test_check_trailing_stop_triggers_on_drawdown(self, tmp_path, monkeypatch):
        """Triggers SELL_ALL when price drops 15%+ below peak."""
        from strategies.ares import check_trailing_stop, HIGH_WATER_PATH
        import json

        hwm = {"ares": {"MAYBANK": 10.00}}
        hwm_file = tmp_path / "hwm.json"
        hwm_file.write_text(json.dumps(hwm))
        monkeypatch.setattr("strategies.ares.HIGH_WATER_PATH", hwm_file)

        holdings = {"MAYBANK": {"shares": 1000, "cost": 10.00}}
        prices = {"MAYBANK": 8.00}  # 20% drop from peak 10.00

        trades = check_trailing_stop("ares", holdings, prices)
        assert len(trades) == 1
        assert trades[0]["action"] == "SELL_ALL"
        assert trades[0]["stock"] == "MAYBANK"
        assert trades[0]["source"] == "trailing_stop"

    def test_check_trailing_stop_triggers_exactly_at_threshold(self, tmp_path, monkeypatch):
        """Triggers when drawdown is exactly 15% (<= -trailing_pct)."""
        from strategies.ares import check_trailing_stop, HIGH_WATER_PATH
        import json

        hwm = {"ares": {"MAYBANK": 10.00}}
        hwm_file = tmp_path / "hwm.json"
        hwm_file.write_text(json.dumps(hwm))
        monkeypatch.setattr("strategies.ares.HIGH_WATER_PATH", hwm_file)

        holdings = {"MAYBANK": {"shares": 1000, "cost": 10.00}}
        prices = {"MAYBANK": 8.50}  # 15% exactly

        trades = check_trailing_stop("ares", holdings, prices)
        assert len(trades) == 1  # <= -15% triggers

    def test_update_high_water_marks_initializes_new(self, tmp_path, monkeypatch):
        """New positions get initialized with current price."""
        from strategies.ares import update_high_water_marks, HIGH_WATER_PATH

        monkeypatch.setattr("strategies.ares.HIGH_WATER_PATH", tmp_path / "hwm.json")

        holdings = {"MAYBANK": {"shares": 1000, "cost": 10.00}}
        prices = {"MAYBANK": 10.50}

        marks = update_high_water_marks("ares", holdings, prices)
        assert marks["MAYBANK"] == 10.50

    def test_update_high_water_marks_raises_peak(self, tmp_path, monkeypatch):
        """Peak is raised when price exceeds previous high."""
        from strategies.ares import update_high_water_marks, HIGH_WATER_PATH
        import json

        hwm = {"ares": {"MAYBANK": 10.00}}
        hwm_file = tmp_path / "hwm.json"
        hwm_file.write_text(json.dumps(hwm))
        monkeypatch.setattr("strategies.ares.HIGH_WATER_PATH", hwm_file)

        holdings = {"MAYBANK": {"shares": 1000, "cost": 10.00}}
        prices = {"MAYBANK": 11.00}

        marks = update_high_water_marks("ares", holdings, prices)
        assert marks["MAYBANK"] == 11.00


class TestRSI:
    """Tests for scripts/strategies/rsi.py."""

    def test_rsi_from_prices_uptrend(self):
        """RSI should be high for a strong uptrend."""
        from strategies.rsi import compute_rsi_from_prices

        prices = [10.0 + i * 0.5 for i in range(20)]
        rsi = compute_rsi_from_prices(prices)
        assert rsi is not None
        assert rsi > 50, f"Expected RSI > 50 for uptrend, got {rsi}"

    def test_rsi_from_prices_downtrend(self):
        """RSI should be low for a strong downtrend."""
        from strategies.rsi import compute_rsi_from_prices

        prices = [20.0 - i * 0.5 for i in range(20)]
        rsi = compute_rsi_from_prices(prices)
        assert rsi is not None
        assert rsi < 50, f"Expected RSI < 50 for downtrend, got {rsi}"

    def test_rsi_from_prices_all_gains(self):
        """RSI = 100 when there are no losses."""
        from strategies.rsi import compute_rsi_from_prices

        prices = [10.0 + i for i in range(20)]
        rsi = compute_rsi_from_prices(prices)
        assert rsi == 100.0

    def test_rsi_from_prices_all_losses(self):
        """RSI = 0 when there are no gains."""
        from strategies.rsi import compute_rsi_from_prices

        prices = [20.0 - i for i in range(20)]
        rsi = compute_rsi_from_prices(prices)
        assert rsi == 0.0

    def test_rsi_insufficient_data(self):
        """Returns None when not enough prices."""
        from strategies.rsi import compute_rsi_from_prices

        rsi = compute_rsi_from_prices([10.0, 10.5, 11.0])
        assert rsi is None

    def test_cached_rsi_check(self):
        """Cache should be cleared between runs."""
        from strategies.rsi import clear_cache, _rsi_cache

        _rsi_cache["TEST"] = 50.0
        assert len(_rsi_cache) == 1
        clear_cache()
        assert len(_rsi_cache) == 0
