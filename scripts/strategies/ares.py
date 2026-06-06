"""Ares hyper-momentum strategy - trailing stop-loss implementation.

Ares rides winners aggressively. The trailing stop protects gains by
exiting when a position falls 15% below its highest price since entry
(not from cost basis). This locks in profits from rallies while still
allowing the position room to breathe.
"""

from __future__ import annotations

import json
from pathlib import Path

TRAILING_STOP_PCT = 0.15  # Exit when drawdown from peak exceeds 15%
HIGH_WATER_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "high_water_marks.json"


def load_high_water_marks() -> dict:
    """Load persisted peak prices per portfolio+stock.

    Returns dict keyed by portfolio_id, each value a dict of {stock_name: peak_price}.
    """
    if not HIGH_WATER_PATH.exists():
        return {}
    try:
        with open(HIGH_WATER_PATH) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_high_water_marks(marks: dict) -> None:
    """Persist high water marks to disk."""
    HIGH_WATER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(HIGH_WATER_PATH, "w") as f:
        json.dump(marks, f, indent=2)


def update_high_water_marks(portfolio_id: str, holdings: dict, prices: dict) -> dict:
    """Update and return high water marks for a portfolio.

    For each holding, if the current price exceeds the stored peak,
    raise the high water mark. New positions start with the current price.

    Returns the updated marks dict for the given portfolio_id.
    """
    all_marks = load_high_water_marks()
    pid_marks = all_marks.get(portfolio_id, {})

    for name, h in holdings.items():
        current_price = prices.get(name, h.get("cost", 0))
        if current_price <= 0:
            continue
        previous_peak = pid_marks.get(name)
        if previous_peak is None:
            # New position — initialize high water mark
            pid_marks[name] = round(current_price, 4)
        elif current_price > previous_peak:
            # New peak — raise the high water mark
            pid_marks[name] = round(current_price, 4)

    all_marks[portfolio_id] = pid_marks
    save_high_water_marks(all_marks)
    return pid_marks


def check_trailing_stop(
    portfolio_id: str,
    holdings: dict,
    prices: dict,
    trailing_pct: float = TRAILING_STOP_PCT,
) -> list[dict]:
    """Evaluate trailing stop-loss signals for Ares.

    For each position, compares current price against the historical peak
    (high water mark). If drawdown exceeds trailing_pct, returns a SELL_ALL
    trade signal.

    Args:
        portfolio_id: e.g. "ares"
        holdings: {stock_name: {shares, cost, ...}}
        prices: {stock_name: current_price}
        trailing_pct: decimal threshold (default 0.15 = 15%)

    Returns:
        List of trade dicts: {"action": "SELL_ALL", "stock": name, "reason": str, ...}
    """
    all_marks = load_high_water_marks()
    pid_marks = all_marks.get(portfolio_id, {})
    trades = []

    for name, h in holdings.items():
        current_price = prices.get(name, h.get("cost", 0))
        if current_price <= 0:
            continue

        peak = pid_marks.get(name, current_price)
        if peak <= 0:
            continue

        drawdown = (current_price - peak) / peak

        if drawdown <= -trailing_pct:
            trades.append({
                "action": "SELL_ALL",
                "stock": name,
                "shares": h.get("shares", 0),
                "price": current_price,
                "reason": (
                    f"Trailing stop: {drawdown*100:.1f}% from peak RM{peak:.3f} "
                    f"(≥{trailing_pct*100:.0f}% threshold)"
                ),
                "source": "trailing_stop",
                "signal": {},
            })

    return trades


def get_peak_info(portfolio_id: str, stock_name: str) -> dict | None:
    """Get peak price info for a specific position. Used by frontend display."""
    marks = load_high_water_marks()
    pid_marks = marks.get(portfolio_id, {})
    peak = pid_marks.get(stock_name)
    if peak is None:
        return None
    return {"peak_price": peak, "trailing_stop_pct": TRAILING_STOP_PCT}
