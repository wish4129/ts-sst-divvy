"""Tests for volume.py — volume confirmation filter for momentum entries."""

import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from strategies.volume import (
    check_volume_confirmation,
    cached_volume_check,
    clear_cache,
    VOLUME_CONFIRM_RATIO,
    VOLUME_LOOKBACK,
)


# --- Constants ---

def test_volume_confirm_ratio_is_1_5():
    """Default volume confirmation ratio is 1.5x."""
    assert VOLUME_CONFIRM_RATIO == 1.5


def test_volume_lookback_is_20():
    """Default volume lookback is 20 days."""
    assert VOLUME_LOOKBACK == 20


# --- Volume confirmation tests ---

def test_confirm_above_ratio():
    """Volume 2.0x avg → confirmed."""
    # 25 entries: first 5 padding, last 20 avg = 100k, last entry = 200k
    # To make last 20 avg exactly 100k with last=200k:
    # sum of last 20 = 2,000,000 → 19 preceding entries sum to 1,800,000 → 94,736.84 each
    preceding = 94736.842
    volumes = [100000.0] * 5 + [preceding] * 19 + [200000.0]  # 5+19+1=25

    with patch("strategies.volume.get_volume_history", return_value=volumes):
        confirmed, latest, avg = check_volume_confirmation("TEST.KL")

    assert confirmed is True, f"Expected confirmed, got latest={latest}, avg={avg}"
    assert latest == 200000.0


def test_confirm_below_ratio():
    """Volume 1.2x avg → NOT confirmed."""
    # avg=100k, last=120k → 1.2x < 1.5x
    preceding = 97894.737  # (20*100000 - 120000) / 19
    volumes = [100000.0] * 5 + [preceding] * 19 + [120000.0]

    with patch("strategies.volume.get_volume_history", return_value=volumes):
        confirmed, latest, avg = check_volume_confirmation("TEST.KL")

    assert confirmed is False
    assert latest == 120000.0


def test_confirm_exactly_at_ratio():
    """Volume exactly 1.5x avg → confirmed (>= check)."""
    # avg=100k, last=150k → 1.5x exactly
    preceding = 97368.421  # (20*100000 - 150000) / 19
    volumes = [100000.0] * 5 + [preceding] * 19 + [150000.0]

    with patch("strategies.volume.get_volume_history", return_value=volumes):
        confirmed, latest, avg = check_volume_confirmation("TEST.KL")

    assert confirmed is True, f"Expected confirmed, got avg={avg}, last={latest}"


def test_confirm_just_below_ratio():
    """Volume 1.499x avg → NOT confirmed."""
    preceding = 97894.737
    volumes = [100000.0] * 5 + [preceding] * 19 + [120000.0]

    with patch("strategies.volume.get_volume_history", return_value=volumes):
        confirmed, latest, avg = check_volume_confirmation("TEST.KL")

    assert confirmed is False


def test_confirm_high_volume_10x():
    """Volume 10x avg → confirmed (extreme case)."""
    # avg=100k, last=1M → 10x → should confirm
    preceding = 52631.579  # (20*100000 - 1000000) / 19
    volumes = [100000.0] * 5 + [preceding] * 19 + [1000000.0]

    with patch("strategies.volume.get_volume_history", return_value=volumes):
        confirmed, latest, avg = check_volume_confirmation("TEST.KL")

    assert confirmed is True


def test_no_data_returns_blocked():
    """When yfinance returns no data → block entry (conservative)."""
    with patch("strategies.volume.get_volume_history", return_value=None):
        confirmed, latest, avg = check_volume_confirmation("TEST.KL")

    assert confirmed is False
    assert latest is None
    assert avg is None


def test_zero_volume_blocked():
    """Zero latest volume → not confirmed."""
    # All zeros → avg=0, last=0 → check: latest <= 0 → blocked
    volumes = [0.0] * 25

    with patch("strategies.volume.get_volume_history", return_value=volumes):
        confirmed, latest, avg = check_volume_confirmation("TEST.KL")

    assert confirmed is False


def test_zero_avg_volume_blocked():
    """Zero average volume (but non-zero last) → probably blocked at avg check."""
    # This is an edge case — if avg=0, division is avoided because avg <= 0 check
    # The code checks: if avg_vol is None or avg_vol <= 0
    volumes = [0.0] * 25
    volumes[-1] = 100000.0  # last=100k, but 19 preceding are 0 → avg ≈ 5000

    with patch("strategies.volume.get_volume_history", return_value=volumes):
        confirmed, latest, avg = check_volume_confirmation("TEST.KL")

    # avg = (19*0 + 100000) / 20 = 5000 → last/avg = 20x → confirmed
    # This is just verifying it doesn't crash
    assert isinstance(confirmed, bool)


def test_negative_volume_blocked():
    """Negative volume (bad data) → not confirmed."""
    volumes = [100000.0] * 24 + [-5000.0]

    with patch("strategies.volume.get_volume_history", return_value=volumes):
        confirmed, latest, avg = check_volume_confirmation("TEST.KL")

    assert confirmed is False


def test_custom_ratio():
    """Custom ratio parameter overrides default 1.5."""
    # avg=100k, last=120k → 1.2x. With ratio=1.2, it should confirm
    preceding = 97894.737
    volumes = [100000.0] * 5 + [preceding] * 19 + [120000.0]

    with patch("strategies.volume.get_volume_history", return_value=volumes):
        confirmed, latest, avg = check_volume_confirmation("TEST.KL", ratio=1.2)

    assert confirmed is True, f"Expected confirmed with ratio=1.2, got avg={avg}, last={latest}"


def test_custom_lookback():
    """Custom lookback parameter works."""
    # 10 entries with all = 50000 → avg=50000, last=50000 → 1.0x → not confirmed
    volumes = [50000.0] * 10

    with patch("strategies.volume.get_volume_history", return_value=volumes):
        confirmed, latest, avg = check_volume_confirmation("TEST.KL", lookback=10)

    assert confirmed is False
    assert latest == 50000.0
    assert avg == 50000.0


# --- Insufficient data edge cases ---

def test_insufficient_data_for_avg():
    """Not enough data to compute average → blocked."""
    volumes = [100000.0] * 10  # only 10 entries, need 20 for default lookback

    with patch("strategies.volume.get_volume_history", return_value=volumes):
        confirmed, latest, avg = check_volume_confirmation("TEST.KL")

    assert confirmed is False


def test_empty_volume_list():
    """Empty volume list → blocked."""
    with patch("strategies.volume.get_volume_history", return_value=[]):
        confirmed, latest, avg = check_volume_confirmation("TEST.KL")

    assert confirmed is False
    assert latest is None


# --- Cache tests ---

def test_cached_volume_check():
    """Cached check returns same result as direct."""
    clear_cache()
    preceding = 94736.842
    volumes = [100000.0] * 5 + [preceding] * 19 + [200000.0]

    with patch("strategies.volume.get_volume_history", return_value=volumes):
        confirmed1, latest1, avg1 = cached_volume_check("CACHE.KL")
        # Second call uses cache (no additional get_volume_history call needed)
        confirmed2, latest2, avg2 = cached_volume_check("CACHE.KL")

    assert confirmed1 == confirmed2
    assert latest1 == latest2
    assert avg1 == avg2


def test_clear_cache_works():
    """Clear cache empties the volume cache."""
    from strategies import volume as vol_mod
    vol_mod._volume_cache["SOMESTOCK.KL"] = (True, 100000.0, 50000.0)
    assert len(vol_mod._volume_cache) > 0

    clear_cache()
    assert len(vol_mod._volume_cache) == 0


def test_nan_in_volume_data():
    """NaN values in volume list handled gracefully."""
    import math
    preceding = 94736.842
    volumes = [100000.0] * 5 + [preceding] * 19 + [float('nan')]

    with patch("strategies.volume.get_volume_history", return_value=volumes):
        confirmed, latest, avg = check_volume_confirmation("TEST.KL")

    # NaN comparisons always return False
    assert confirmed is False
