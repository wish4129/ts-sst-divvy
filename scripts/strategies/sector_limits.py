"""Sector exposure limits — cap single-sector allocation at 50%.

Prevents concentration in any single Bursa sector. Enforced at BUY time —
no new entry that would push a sector above the cap. Rebalanced organically
as other sectors grow or the capped sector declines.

Usage (from portfolio_manager.py):
    from strategies.sector_limits import check_sector_exposure, SECTOR_LIMIT

    # Before executing a BUY trade:
    if not check_sector_exposure(pid, proposed_stock, proposed_value,
                                  holdings, prices, cash, stock_map):
        print(f"  [{pid}] Sector limit: skipping BUY {proposed_stock}")
        continue
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from persona_db import get_all_stocks_dict

SECTOR_LIMIT = 0.50  # Max 50% in any single sector


def _get_stock_sectors() -> Dict[str, str]:
    """Get {short_name: industry} mapping from DB."""
    stocks = get_all_stocks_dict()
    return {
        short: info.get("industry", "Unknown")
        for short, info in stocks.items()
    }


def _normalize_sector(industry: str) -> str:
    """Merge similar industries into broader sectors for exposure limits.

    Groups e.g. 'Banking' and 'Credit Services' into 'Financials'.
    """
    sector_map = {
        "Banking": "Financials",
        "Credit Services": "Financials",
        "Investment": "Financials",
        "REIT": "REITs",
        "Real Estate - Development": "Property",
        "Property": "Property",
        "Construction": "Construction & Engineering",
        "Engineering & Construction": "Construction & Engineering",
        "Oil & Gas Equipment & Services": "Energy",
        "Energy": "Energy",
        "Semiconductor": "Technology",
        "Tech": "Technology",
        "Telco": "Telecommunications",
        "Consumer": "Consumer",
        "Consumer Products & Services": "Consumer",
        "Farm Products": "Agriculture",
        "Plantation": "Agriculture",
        "Metal Fabrication": "Industrials",
        "Industrial": "Industrials",
        "Packaging": "Industrials",
        "Furniture": "Consumer",
        "Automotive": "Consumer",
        "Conglomerate": "Conglomerate",
        "Utilities": "Utilities",
        "Main Market": "Diversified",
    }
    return sector_map.get(industry, industry)


def get_sector(stock_name: str) -> str:
    """Get the normalized sector for a stock."""
    sectors = _get_stock_sectors()
    raw = sectors.get(stock_name, "Unknown")
    return _normalize_sector(raw)


def get_persona_sector_exposure(
    holdings: Dict[str, dict],
    prices: Dict[str, float],
) -> Dict[str, float]:
    """Calculate current sector exposure for a persona's portfolio.

    Args:
        holdings: {stock_name: {shares, cost, ...}}
        prices: {stock_name: current_price}

    Returns:
        {sector: exposure_pct} e.g. {'Financials': 0.35, 'REITs': 0.15}
    """
    sector_values: Dict[str, float] = {}
    total_value = 0.0

    for name, h in holdings.items():
        price = prices.get(name, h.get("cost", 0))
        value = h.get("shares", 0) * price
        sector = get_sector(name)
        sector_values[sector] = sector_values.get(sector, 0) + value
        total_value += value

    if total_value <= 0:
        return {}

    return {s: round(v / total_value, 4) for s, v in sector_values.items()}


def check_sector_exposure(
    persona_id: str,
    stock_name: str,
    proposed_value: float,
    holdings: Dict[str, dict],
    prices: Dict[str, float],
    cash: float,
    stock_map: Optional[Dict] = None,
    limit: float = SECTOR_LIMIT,
) -> bool:
    """Check if adding a position would breach sector limit.

    Args:
        persona_id: 'ares', 'demeter', or 'athena'
        stock_name: Short name of stock to buy
        proposed_value: RM value of proposed buy
        holdings: Current holdings dict
        prices: Current prices dict
        cash: Current cash balance
        stock_map: Unused (kept for API compat with portfolio_manager)
        limit: Maximum sector exposure (default 0.50 = 50%)

    Returns:
        True if BUY is allowed, False if sector limit would be breached.
    """
    # Get current sector exposure
    exposure = get_persona_sector_exposure(holdings, prices)
    target_sector = get_sector(stock_name)

    # Calculate total portfolio value
    total_holdings = sum(
        h.get("shares", 0) * prices.get(n, h.get("cost", 0))
        for n, h in holdings.items()
    )
    new_total = total_holdings + proposed_value + cash

    if new_total <= 0:
        return True  # Can't compute, allow

    # Current sector value + proposed buy
    current_sector_value = sum(
        h.get("shares", 0) * prices.get(n, h.get("cost", 0))
        for n, h in holdings.items()
        if get_sector(n) == target_sector
    )
    new_sector_exposure = (current_sector_value + proposed_value) / new_total

    return new_sector_exposure <= limit


def check_existing_sector_breaches(
    holdings: Dict[str, dict],
    prices: Dict[str, float],
    limit: float = SECTOR_LIMIT,
) -> List[Dict]:
    """Check if any existing sector exposures exceed the limit.

    Returns list of breach warnings (empty if all within limits).
    """
    exposure = get_persona_sector_exposure(holdings, prices)
    breaches = []
    for sector, pct in sorted(exposure.items(), key=lambda x: x[1], reverse=True):
        if pct > limit:
            breaches.append({
                "sector": sector,
                "exposure_pct": round(pct * 100, 1),
                "limit_pct": round(limit * 100, 0),
                "excess_pct": round((pct - limit) * 100, 1),
                "severity": "critical" if pct > limit + 0.10 else "warning",
            })
        elif pct > limit * 0.8:
            breaches.append({
                "sector": sector,
                "exposure_pct": round(pct * 100, 1),
                "limit_pct": round(limit * 100, 0),
                "excess_pct": 0,
                "severity": "approaching",
            })
    return breaches


def get_sector_breakdown(
    holdings: Dict[str, dict],
    prices: Dict[str, float],
) -> List[Dict]:
    """Get detailed sector breakdown for display."""
    exposure = get_persona_sector_exposure(holdings, prices)

    # Per-sector stock details
    sector_stocks: Dict[str, List[Dict]] = {}
    for name, h in holdings.items():
        price = prices.get(name, h.get("cost", 0))
        value = h.get("shares", 0) * price
        sector = get_sector(name)
        sector_stocks.setdefault(sector, []).append({
            "stock": name,
            "value": round(value, 2),
        })

    breakdown = []
    for sector, pct in sorted(exposure.items(), key=lambda x: x[1], reverse=True):
        breakdown.append({
            "sector": sector,
            "exposure_pct": round(pct * 100, 1),
            "stocks": sector_stocks.get(sector, []),
            "status": (
                "over_limit" if pct > SECTOR_LIMIT
                else "approaching" if pct > SECTOR_LIMIT * 0.8
                else "ok"
            ),
        })

    return breakdown
