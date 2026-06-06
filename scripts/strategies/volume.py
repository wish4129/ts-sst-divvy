"""Volume confirmation filter for momentum entries.

Checks whether recent trading volume exceeds the 20-day average
by a configurable ratio (default 1.5x). Used by portfolio_manager
to confirm BUY entries only during high-volume periods - filtering
out low-conviction, low-participation price moves.

Inspired by: "Volume precedes price" - heavy volume on entry day
signals institutional participation and reduces fakeout risk.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from market_data import get_volume_history, compute_avg_volume, get_latest_volume

VOLUME_CONFIRM_RATIO = 1.5  # Recent volume must exceed 20-day avg by this multiple
VOLUME_LOOKBACK = 20         # Days for the moving average


def check_volume_confirmation(
    ticker_code: str,
    ratio: float = VOLUME_CONFIRM_RATIO,
    lookback: int = VOLUME_LOOKBACK,
) -> tuple[bool, float | None, float | None]:
    """Check if recent volume exceeds the 20-day average.

    Returns True (confirmed) when the most recent day's volume is
    >= ratio * 20-day average volume. Returns False when volume is
    insufficient or data is unavailable (conservative: blocks entry).

    Args:
        ticker_code: Ticker in yfinance format (e.g. '1155.KL')
        ratio: Minimum volume multiplier (default 1.5)
        lookback: Days for moving average (default 20)

    Returns:
        (confirmed, latest_volume, avg_volume)
          confirmed=True: entry allowed (high volume)
          confirmed=False, latest is None: data unavailable (conservative block)
          confirmed=False, latest is not None: volume too low
    """
    volumes = get_volume_history(ticker_code, days=lookback + 40)
    if volumes is None:
        return False, None, None  # Data unavailable - block entry

    avg_vol = compute_avg_volume(volumes, lookback)
    latest_vol = get_latest_volume(volumes)

    if avg_vol is None or avg_vol <= 0 or latest_vol is None or latest_vol <= 0:
        return False, latest_vol, avg_vol

    confirmed = latest_vol >= avg_vol * ratio
    return confirmed, latest_vol, avg_vol


# Cache to avoid repeated yfinance calls within a single run
_volume_cache: dict[str, tuple[bool, float | None, float | None]] = {}


def cached_volume_check(ticker_code: str) -> tuple[bool, float | None, float | None]:
    """Cached version of check_volume_confirmation for batch use."""
    if ticker_code not in _volume_cache:
        _volume_cache[ticker_code] = check_volume_confirmation(ticker_code)
    return _volume_cache[ticker_code]


def clear_cache() -> None:
    """Clear the volume cache between runs."""
    _volume_cache.clear()
