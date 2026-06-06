"""Market data fetcher - shared yfinance layer for strategies.

Provides OHLCV + volume data so individual strategy modules
don't each call yfinance independently. Used by volume.py, rsi.py, etc.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

# Ensure scripts/ is on path for db import
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

try:
    import yfinance as yf
except ImportError:
    import os
    os.system(f"{sys.executable} -m pip install yfinance --quiet")
    import yfinance as yf

VOLUME_LOOKBACK_DAYS = 60  # Fetch this many days to compute 20-day avg safely


def get_volume_history(ticker_code: str, days: int = VOLUME_LOOKBACK_DAYS) -> Optional[list[float]]:
    """Fetch daily volume for a stock.

    Args:
        ticker_code: Ticker in yfinance format (e.g. '1155.KL' for Maybank)
        days: Number of trading days to fetch (default 60 = enough for 20-day avg)

    Returns:
        List of daily volumes (most recent last), or None if data unavailable.
    """
    try:
        ticker = yf.Ticker(ticker_code)
        hist = ticker.history(period=f"{days + 10}d")  # extra buffer for weekends/holidays
        if hist.empty or "Volume" not in hist.columns:
            return None
        volumes = hist["Volume"].dropna().tolist()
        if len(volumes) < 3:
            return None
        return volumes
    except Exception:
        return None


def get_ohlcv(ticker_code: str, days: int = 30) -> Optional[dict]:
    """Fetch recent OHLCV data for a stock.

    Returns:
        Dict with keys: closes, volumes, highs, lows, opens (all lists, recent last)
        None if data unavailable.
    """
    try:
        ticker = yf.Ticker(ticker_code)
        hist = ticker.history(period=f"{days + 10}d")
        if hist.empty or len(hist) < 3:
            return None
        return {
            "closes": hist["Close"].dropna().tolist(),
            "volumes": hist["Volume"].dropna().tolist(),
            "highs": hist["High"].dropna().tolist(),
            "lows": hist["Low"].dropna().tolist(),
            "opens": hist["Open"].dropna().tolist(),
        }
    except Exception:
        return None


def compute_avg_volume(volumes: list[float], window: int = 20) -> Optional[float]:
    """Compute average volume over the last `window` days.

    Args:
        volumes: List of daily volumes (most recent last)
        window: Number of days to average (default 20)

    Returns:
        Average volume, or None if insufficient data.
    """
    if len(volumes) < window:
        return None
    return sum(volumes[-window:]) / window


def get_latest_volume(volumes: list[float]) -> Optional[float]:
    """Get the most recent day's volume."""
    if not volumes:
        return None
    return volumes[-1]
