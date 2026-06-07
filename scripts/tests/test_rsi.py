"""Tests for rsi.py — RSI-14 filter for entry signals."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from strategies.rsi import (
    compute_rsi_from_prices,
    _calc_rsi,
    cached_rsi_check,
    clear_cache,
    RSI_PERIOD,
    RSI_OVERBOUGHT,
    RSI_OVERSOLD,
)


# --- RSI Calculation (pure function) ---

def test_rsi_period_is_14():
    """Default RSI period is 14."""
    assert RSI_PERIOD == 14


def test_rsi_overbought_threshold_is_70():
    """Overbought threshold is 70."""
    assert RSI_OVERBOUGHT == 70


def test_rsi_oversold_threshold_is_30():
    """Oversold threshold is 30."""
    assert RSI_OVERSOLD == 30


def test_calc_rsi_uniform_prices():
    """All prices same → no gains or losses → RSI = 100."""
    prices = [10.0] * 20  # 20 identical prices
    result = _calc_rsi(prices, period=14)
    assert result == 100.0


def test_calc_rsi_all_gains():
    """Monotonically increasing prices → high RSI."""
    prices = [float(i) for i in range(1, 21)]  # 1, 2, 3, ..., 20
    result = _calc_rsi(prices, period=14)
    assert result > 90.0  # Almost all gains → high RSI


def test_calc_rsi_all_losses():
    """Monotonically decreasing prices → low RSI."""
    prices = [float(20 - i) for i in range(20)]  # 20, 19, ..., 1
    result = _calc_rsi(prices, period=14)
    assert result < 10.0  # Almost all losses → low RSI


def test_calc_rsi_typical_range():
    """RSI always returns between 0 and 100."""
    # Mixed prices with some volatility
    prices = [
        10.0, 10.5, 10.3, 10.8, 10.6, 10.9, 10.4, 10.2,
        10.7, 11.0, 10.8, 10.5, 10.3, 10.1, 10.4, 10.6,
        10.9, 10.7, 10.5, 10.8,
    ]
    result = _calc_rsi(prices, period=14)
    assert 0 <= result <= 100


def test_calc_rsi_with_known_values():
    """Verify RSI against manually computed expected value."""
    # Simple alternating up/down pattern
    prices = [
        10.0, 10.2, 10.0, 10.2, 10.0, 10.2, 10.0, 10.2,
        10.0, 10.2, 10.0, 10.2, 10.0, 10.2, 10.0, 10.2,
    ]
    result = _calc_rsi(prices, period=14)
    # Alternating equal gains/losses → roughly 50
    assert 45 <= result <= 55


def test_calc_rsi_empty_prices():
    """Not enough data returns None from the wrapper."""
    result = compute_rsi_from_prices([10.0], period=14)
    assert result is None


def test_calc_rsi_exactly_minimum_data():
    """With exactly period+1 data points, RSI is computed."""
    prices = [10.0 + (i * 0.1) for i in range(15)]  # 15 points = 14 + 1
    result = compute_rsi_from_prices(prices, period=14)
    assert result is not None
    assert 0 <= result <= 100


# --- compute_rsi_from_prices tests ---

def test_compute_rsi_from_prices_insufficient_data():
    """Returns None when fewer than period+1 prices."""
    result = compute_rsi_from_prices([10.0, 10.5, 10.3], period=14)
    assert result is None


def test_compute_rsi_from_prices_sufficient_data():
    """Returns valid RSI when enough data points."""
    prices = [float(i) for i in range(1, 20)]  # 19 points
    result = compute_rsi_from_prices(prices, period=14)
    assert result is not None
    assert 0 <= result <= 100


def test_compute_rsi_from_prices_custom_period():
    """Works with non-default period."""
    prices = [float(i) for i in range(1, 10)]  # 9 points
    result = compute_rsi_from_prices(prices, period=5)
    assert result is not None
    assert 0 <= result <= 100


# --- Overbought / Oversold threshold tests via cache ---
# These test the threshold comparison logic in cached_rsi_check()

def test_skip_entry_when_overbought():
    """BUY should be skipped when RSI > 70 (overbought)."""
    clear_cache()
    from strategies import rsi as rsi_mod
    rsi_mod._rsi_cache["OVER.KL"] = 72.0
    skip, rsi = cached_rsi_check("OVER.KL")
    assert skip is True
    assert rsi == 72.0


def test_allow_entry_when_neutral():
    """BUY allowed when RSI between 30-70."""
    clear_cache()
    from strategies import rsi as rsi_mod
    rsi_mod._rsi_cache["NEUT.KL"] = 55.0
    skip, rsi = cached_rsi_check("NEUT.KL")
    assert skip is False


def test_allow_entry_when_oversold():
    """BUY allowed when RSI < 30 (oversold is bullish signal)."""
    clear_cache()
    from strategies import rsi as rsi_mod
    rsi_mod._rsi_cache["OVER.KL"] = 25.0
    skip, rsi = cached_rsi_check("OVER.KL")
    assert skip is False


# --- Cache tests ---

def test_cached_rsi_check_overbought():
    """Cached check returns skip=True for overbought RSI."""
    clear_cache()

    # Prime the cache directly
    from strategies import rsi as rsi_mod
    rsi_mod._rsi_cache["TEST.KL"] = 72.0

    skip, value = cached_rsi_check("TEST.KL")
    assert skip is True
    assert value == 72.0


def test_cached_rsi_check_neutral():
    """Cached check returns skip=False for neutral RSI."""
    clear_cache()

    from strategies import rsi as rsi_mod
    rsi_mod._rsi_cache["TEST2.KL"] = 55.0

    skip, value = cached_rsi_check("TEST2.KL")
    assert skip is False
    assert value == 55.0


def test_cached_rsi_check_oversold():
    """Cached check returns skip=False for oversold RSI."""
    clear_cache()

    from strategies import rsi as rsi_mod
    rsi_mod._rsi_cache["TEST3.KL"] = 25.0

    skip, value = cached_rsi_check("TEST3.KL")
    assert skip is False
    assert value == 25.0


def test_cached_rsi_check_exactly_at_threshold():
    """RSI exactly at 70 → overbought (>= check)."""
    clear_cache()

    from strategies import rsi as rsi_mod
    rsi_mod._rsi_cache["TEST4.KL"] = 70.0

    skip, value = cached_rsi_check("TEST4.KL")
    assert skip is True


def test_cached_rsi_check_just_below_threshold():
    """RSI at 69.9 → NOT overbought."""
    clear_cache()

    from strategies import rsi as rsi_mod
    rsi_mod._rsi_cache["TEST5.KL"] = 69.9

    skip, value = cached_rsi_check("TEST5.KL")
    assert skip is False


def test_cached_rsi_check_none_value():
    """None RSI (no data) → skip=False (don't block entry)."""
    clear_cache()

    from strategies import rsi as rsi_mod
    rsi_mod._rsi_cache["TEST6.KL"] = None

    skip, value = cached_rsi_check("TEST6.KL")
    assert skip is False
    assert value is None


def test_clear_cache_works():
    """Clear cache empties the RSI cache."""
    from strategies import rsi as rsi_mod
    rsi_mod._rsi_cache["SOMESTOCK.KL"] = 50.0
    assert len(rsi_mod._rsi_cache) > 0

    clear_cache()
    assert len(rsi_mod._rsi_cache) == 0
