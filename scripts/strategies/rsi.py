"""RSI (Relative Strength Index) filter for entry signals.

Computes RSI-14 from yfinance price history. Used by all 3 persona
strategies to skip BUY entries when RSI > 70 (overbought territory).
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure scripts/ is on path for db import
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

try:
    import yfinance as yf
except ImportError:
    import os
    os.system(f"{sys.executable} -m pip install yfinance --quiet")
    import yfinance as yf

RSI_PERIOD = 14
RSI_OVERBOUGHT = 70  # Skip entries when RSI exceeds this
RSI_OVERSOLD = 30    # Optional: bullish on oversold (future use)


def compute_rsi(ticker_code: str, period: int = RSI_PERIOD) -> float | None:
    """Compute RSI for a stock from yfinance price history.

    Args:
        ticker_code: Ticker in yfinance format (e.g. '1155.KL' for Maybank)
        period: Lookback period for RSI calculation (default 14)

    Returns:
        RSI value (0-100), or None if data unavailable.
    """
    try:
        ticker = yf.Ticker(ticker_code)
        hist = ticker.history(period="2mo")
        if len(hist) < period + 1:
            return None
        closes = hist["Close"].values
        return _calc_rsi(closes, period)
    except Exception:
        return None


def compute_rsi_from_prices(prices: list[float], period: int = RSI_PERIOD) -> float | None:
    """Compute RSI from a list of closing prices."""
    if len(prices) < period + 1:
        return None
    return _calc_rsi(prices, period)


def _calc_rsi(closes, period: int) -> float:
    """Standard RSI calculation using Wilder's smoothing."""
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]

    # Initial average
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    # Wilder's smoothing for remaining periods
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def should_skip_entry(ticker_code: str, overbought: float = RSI_OVERBOUGHT) -> tuple[bool, float | None]:
    """Check if stock is overbought — skip BUY entries if RSI > threshold.

    Returns:
        (skip, rsi_value) — True means skip the BUY.
    """
    rsi = compute_rsi(ticker_code)
    if rsi is None:
        return False, None  # No data — don't block entry
    return rsi >= overbought, rsi


# Cache to avoid repeated yfinance calls within a single run
_rsi_cache: dict[str, float | None] = {}


def cached_rsi_check(ticker_code: str) -> tuple[bool, float | None]:
    """Cached version of should_skip_entry for batch use."""
    if ticker_code not in _rsi_cache:
        _rsi_cache[ticker_code] = compute_rsi(ticker_code)
    rsi = _rsi_cache[ticker_code]
    if rsi is None:
        return False, None
    return rsi >= RSI_OVERBOUGHT, rsi


def clear_cache() -> None:
    """Clear the RSI cache between runs."""
    _rsi_cache.clear()
