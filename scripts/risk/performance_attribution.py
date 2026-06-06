#!/usr/bin/env python3
"""Performance attribution report — decompose portfolio returns by factor.

Attributes P&L to: sector allocation, stock selection, market timing,
dividend contribution, and trading costs. Provides insight into which
persona strategies are generating alpha and where.

Usage:
  cd ~/xiongit/divvy && .venv/bin/python3 scripts/risk/performance_attribution.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db import get_db
from persona_db import get_all_stocks_dict, TICKER_TO_SHORT, SHORT_TO_TICKER
from strategies.sector_limits import get_sector
from risk.monte_carlo import fetch_returns as fetch_returns_matrix
from risk.transaction_costs import round_trip_cost, BROKERAGE_RATE

ROOT = Path(__file__).resolve().parent.parent.parent
MALAYSIA_TZ = timezone(timedelta(hours=8))
HISTORY_YEARS = 2.0


def load_trade_history(persona_id: str) -> List[Dict]:
    """Load executed trades for a persona from DB."""
    db = get_db()
    cur = db.cursor()
    cur.execute(
        """SELECT t.stock_id, t.action, t.shares, t.price, t.total_amount,
                  t.reason, t.decision_source, t.executed_at
           FROM trades t
           JOIN user_portfolios up ON up.id = t.portfolio_id
           WHERE up.persona = %s
           ORDER BY t.executed_at DESC
           LIMIT 500""",
        (persona_id,),
    )
    trades = []
    for row in cur.fetchall():
        trades.append({
            "stock_id": row[0],
            "action": row[1],
            "shares": row[2],
            "price": float(row[3]),
            "total_amount": float(row[4]) if row[4] else 0,
            "reason": row[5],
            "source": row[6],
            "executed_at": row[7].isoformat() if row[7] else None,
        })
    cur.close()
    db.close()
    return trades


def load_snapshot_history(persona_id: str) -> List[Dict]:
    """Load portfolio snapshots for performance timeline."""
    db = get_db()
    cur = db.cursor()
    cur.execute(
        """SELECT ps.snapshot_at, ps.total_value, ps.invested, ps.cash,
                  ps.pnl, ps.pnl_pct, ps.holdings_json
           FROM portfolio_snapshots ps
           JOIN user_portfolios up ON up.id = ps.portfolio_id
           WHERE up.persona = %s
           ORDER BY ps.snapshot_at ASC""",
        (persona_id,),
    )
    snapshots = []
    for row in cur.fetchall():
        h = row[6] if isinstance(row[6], dict) else (json.loads(row[6]) if row[6] else {})
        snapshots.append({
            "at": row[0].isoformat() if row[0] else None,
            "total_value": float(row[1]),
            "invested": float(row[2]),
            "cash": float(row[3]),
            "pnl": float(row[4]),
            "pnl_pct": float(row[5]),
            "holdings": h,
        })
    cur.close()
    db.close()
    return snapshots


def attribute_returns(
    persona_id: str,
    snapshots: List[Dict],
    trades: List[Dict],
) -> Dict:
    """Decompose portfolio returns into attribution factors.

    Returns dict with attribution breakdown.
    """
    if len(snapshots) < 2:
        return {"error": "Need at least 2 snapshots"}

    first = snapshots[0]
    last = snapshots[-1]

    initial_value = first["total_value"]
    final_value = last["total_value"]
    total_pnl = final_value - initial_value
    total_return_pct = (total_pnl / initial_value * 100) if initial_value > 0 else 0

    # 1. Sector allocation effect
    # Compare sector weights vs equal-weight benchmark
    sector_contribution = 0.0
    if first.get("holdings") and last.get("holdings"):
        sectors_first = _sector_values(first["holdings"])
        sectors_last = _sector_values(last["holdings"])
        n_sectors = max(len(sectors_first), len(sectors_last), 1)
        # Simplification: if we concentrated in winning sectors, that's positive
        sector_contribution = _estimate_sector_effect(sectors_first, sectors_last, n_sectors)

    # 2. Trading cost drag
    total_cost = 0.0
    for t in trades:
        val = t["total_amount"]
        if val > 0:
            if t["action"] in ("BUY", "SELL"):
                cost = round_trip_cost(val) if t["action"] == "BUY" else round_trip_cost(val)
                total_cost += cost["total_round_trip"] / 2  # Half since round-trip counts both

    cost_pct = (total_cost / initial_value * 100) if initial_value > 0 else 0

    # 3. Cash drag (uninvested cash earns ~0%)
    avg_cash_pct = np.mean([s["cash"] / max(s["total_value"], 1) for s in snapshots])
    cash_drag = avg_cash_pct * 0.03 * HISTORY_YEARS * 100  # Opportunity cost vs FD

    # 4. Dividend contribution (estimated from holdings)
    div_contribution = _estimate_dividend_contribution(snapshots)

    # 5. Net attribution
    trading_pnl = total_pnl + total_cost  # Add back costs to get gross trading P&L
    unexplained = total_pnl - (sector_contribution * initial_value / 100 + div_contribution - total_cost)

    return {
        "persona": persona_id,
        "period": {
            "start": first["at"],
            "end": last["at"],
            "n_snapshots": len(snapshots),
        },
        "total_pnl": round(total_pnl, 2),
        "total_return_pct": round(total_return_pct, 2),
        "initial_value": round(initial_value, 2),
        "final_value": round(final_value, 2),
        "attribution": {
            "sector_allocation_estimate": round(sector_contribution, 2),
            "trading_costs": round(-total_cost, 2),
            "trading_costs_pct": round(-cost_pct, 2),
            "cash_drag_estimate": round(-cash_drag, 2),
            "dividend_contribution_estimate": round(div_contribution, 2),
            "net_trading_pnl": round(trading_pnl, 2),
            "unexplained": round(unexplained, 2),
        },
        "trade_summary": {
            "n_trades": len(trades),
            "n_buys": sum(1 for t in trades if t["action"] == "BUY"),
            "n_sells": sum(1 for t in trades if t["action"] in ("SELL", "SELL_ALL")),
            "total_turnover_rm": round(sum(abs(t["total_amount"]) for t in trades), 2),
            "avg_trade_size": round(np.mean([abs(t["total_amount"]) for t in trades]), 2) if trades else 0,
        },
        "trade_sources": _count_sources(trades),
    }


def _sector_values(holdings: Dict) -> Dict[str, float]:
    """Calculate sector values from holdings."""
    sectors: Dict[str, float] = {}
    for name, h in holdings.items():
        sector = get_sector(name)
        value = h.get("shares", 0) * h.get("price", h.get("cost", 0))
        sectors[sector] = sectors.get(sector, 0) + value
    return sectors


def _estimate_sector_effect(
    first: Dict[str, float],
    last: Dict[str, float],
    n_sectors: int,
) -> float:
    """Estimate sector allocation contribution."""
    total_first = sum(first.values())
    total_last = sum(last.values())
    if total_first <= 0:
        return 0.0

    effect = 0.0
    all_sectors = set(first.keys()) | set(last.keys())
    for sector in all_sectors:
        w_first = first.get(sector, 0) / total_first
        w_last = last.get(sector, 0) / max(total_last, 1)
        equal_w = 1.0 / max(n_sectors, 1)
        # Positive if we overweighted a sector that grew
        effect += (w_first - equal_w) * (w_last - w_first) * 100

    return round(effect, 2)


def _estimate_dividend_contribution(snapshots: List[Dict]) -> float:
    """Estimate dividend contribution from REIT/div holdings."""
    # Simplification: assume 5% yield on REITs, 3% on others
    total_div = 0.0
    for snap in snapshots[-20:]:  # Last 20 snapshots
        for name, h in snap.get("holdings", {}).items():
            sector = get_sector(name)
            shares = h.get("shares", 0)
            price = h.get("price", h.get("cost", 0))
            value = shares * price
            if sector == "REITs":
                total_div += value * 0.05  # 5% REIT yield
            elif sector in ("Financials", "Telecommunications"):
                total_div += value * 0.04  # 4% high-dividend sectors
            elif value > 0:
                total_div += value * 0.02  # 2% general

    # Annualize and prorate
    if snapshots:
        days = len(snapshots)  # Approximate days
        total_div = total_div * (days / 252) / max(len(snapshots[-20:]), 1)

    return round(total_div, 2)


def _count_sources(trades: List[Dict]) -> Dict[str, int]:
    """Count trades by decision source."""
    sources: Dict[str, int] = {}
    for t in trades:
        src = t.get("source", "unknown")
        sources[src] = sources.get(src, 0) + 1
    return dict(sorted(sources.items(), key=lambda x: x[1], reverse=True))


# ── Main ────────────────────────────────────────────────────────────

def run_attribution(persona_id: Optional[str] = None) -> Dict:
    """Run performance attribution for one or all personas."""
    print(f"\n{'='*60}")
    print("Performance Attribution Report")
    print(f"{'='*60}")

    personas = [persona_id] if persona_id else ["ares", "demeter", "athena"]
    results = {}

    for pid in personas:
        trades = load_trade_history(pid)
        snapshots = load_snapshot_history(pid)

        attr = attribute_returns(pid, snapshots, trades)
        results[pid] = attr

        if "error" in attr:
            print(f"\n  [{pid.upper()}] {attr['error']}")
            continue

        a = attr["attribution"]
        ts = attr["trade_summary"]

        print(f"\n  [{pid.upper()}] Attribution:")
        print(f"    Period: {attr['period']['n_snapshots']} snapshots "
              f"({attr['period']['start'][:10]} → {attr['period']['end'][:10]})")
        print(f"    Total P&L: RM{attr['total_pnl']:+,.2f} ({attr['total_return_pct']:+.2f}%)")
        print(f"    ── Breakdown ──")
        print(f"    Sector allocation:  {a['sector_allocation_estimate']:+8.2f}")
        print(f"    Trading costs:      {a['trading_costs']:+8.2f}  ({a['trading_costs_pct']:+.2f}%)")
        print(f"    Cash drag:          {a['cash_drag_estimate']:+8.2f}")
        print(f"    Dividends (est):    {a['dividend_contribution_estimate']:+8.2f}")
        print(f"    Unexplained:        {a['unexplained']:+8.2f}")
        print(f"    ── Trading ──")
        print(f"    Trades: {ts['n_trades']} ({ts['n_buys']} buys, {ts['n_sells']} sells)")
        print(f"    Turnover: RM{ts['total_turnover_rm']:,.0f}")
        if ts['n_trades'] > 0:
            print(f"    Avg trade: RM{ts['avg_trade_size']:,.0f}")
        if attr["trade_sources"]:
            print(f"    Sources: {attr['trade_sources']}")

    return results


def main():
    persona = None
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i].startswith("--persona="):
            persona = args[i].split("=", 1)[1]
        elif args[i] == "--persona" and i + 1 < len(args):
            i += 1; persona = args[i]
        i += 1

    results = run_attribution(persona_id=persona)

    # Save report
    output_path = ROOT / "data" / "performance_attribution.json"
    output = {
        "generated_at": datetime.now(MALAYSIA_TZ).isoformat(),
        "personas": results,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2))
    print(f"\n  ✓ Report saved to {output_path}")


if __name__ == "__main__":
    main()
