"""Tests for scripts/market_data.py — pure calculation functions."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent  # scripts/tests/../../ = divvy/
sys.path.insert(0, str(ROOT / "scripts"))


class TestComputeAvgVolume:
    """Tests for compute_avg_volume() — 20-day average volume."""

    def test_normal_20_day_average(self):
        """Computes average of last 20 elements."""
        from market_data import compute_avg_volume

        volumes = list(range(1, 31))  # 1..30, 30 elements
        result = compute_avg_volume(volumes, window=20)
        # Last 20: 11..30, avg = (11+30)/2 = 20.5
        assert result == 20.5

    def test_window_larger_than_data(self):
        """Returns None when volumes list is shorter than window."""
        from market_data import compute_avg_volume

        volumes = [100, 200, 300]  # 3 elements, window=20
        result = compute_avg_volume(volumes, window=20)
        assert result is None

    def test_exact_window_size(self):
        """Works when volumes list exactly matches window size."""
        from market_data import compute_avg_volume

        volumes = [10, 20, 30, 40, 50]
        result = compute_avg_volume(volumes, window=5)
        assert result == 30.0

    def test_custom_window(self):
        """Supports custom window sizes (not just 20)."""
        from market_data import compute_avg_volume

        volumes = [10, 20, 30, 40, 50]
        result = compute_avg_volume(volumes, window=3)
        # Last 3: 30, 40, 50 -> avg = 40
        assert result == 40.0

    def test_single_element(self):
        """Single-element window works."""
        from market_data import compute_avg_volume

        volumes = [10, 20, 30]
        result = compute_avg_volume(volumes, window=1)
        assert result == 30.0  # last element

    def test_all_zero_volumes(self):
        """Zero volumes average to zero."""
        from market_data import compute_avg_volume

        volumes = [0] * 25
        result = compute_avg_volume(volumes, window=20)
        assert result == 0.0

    def test_mixed_zero_and_positive(self):
        """Mixed zero and non-zero volumes compute correctly."""
        from market_data import compute_avg_volume

        volumes = [0] * 10 + [100] * 10
        result = compute_avg_volume(volumes, window=20)
        assert result == 50.0

    def test_float_volumes(self):
        """Handles float volumes (yfinance sometimes returns floats)."""
        from market_data import compute_avg_volume

        volumes = [1.5, 2.5, 3.5, 4.5, 5.5]
        result = compute_avg_volume(volumes, window=5)
        assert result == 3.5

    def test_large_volumes(self):
        """Handles large volume numbers without overflow."""
        from market_data import compute_avg_volume

        volumes = [1_000_000] * 20
        result = compute_avg_volume(volumes, window=20)
        assert result == 1_000_000.0

    def test_empty_list(self):
        """Returns None for empty list."""
        from market_data import compute_avg_volume

        result = compute_avg_volume([], window=20)
        assert result is None


class TestGetLatestVolume:
    """Tests for get_latest_volume() — most recent day's volume."""

    def test_returns_last_element(self):
        """Returns the last element of the list."""
        from market_data import get_latest_volume

        volumes = [100, 200, 300, 400, 500]
        result = get_latest_volume(volumes)
        assert result == 500

    def test_single_element_list(self):
        """Single-element list returns that element."""
        from market_data import get_latest_volume

        result = get_latest_volume([42])
        assert result == 42

    def test_empty_list(self):
        """Returns None for empty list."""
        from market_data import get_latest_volume

        result = get_latest_volume([])
        assert result is None

    def test_zero_volume(self):
        """Zero volume is returned as-is (not None)."""
        from market_data import get_latest_volume

        result = get_latest_volume([100, 200, 0])
        assert result == 0

    def test_float_volume(self):
        """Float volumes are returned correctly."""
        from market_data import get_latest_volume

        result = get_latest_volume([1.1, 2.2, 3.3])
        assert result == 3.3
