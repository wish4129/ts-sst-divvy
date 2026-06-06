#!/usr/bin/env python3
"""Transaction cost modeling — Bursa Malaysia brokerage, stamp duty, clearing fees.

Models total round-trip costs for accurate P&L calculations and trade
threshold validation. Costs based on standard Bursa Malaysia rates.

Fee structure (Malaysia retail):
  Brokerage:   0.05% - 0.60% (varies by broker, typical online: 0.08-0.15%)
  Stamp duty:  RM1.00 per RM1,000 (0.1%), capped at RM200
  Clearing:    0.03% (max RM1,000)
  SST:         6% on brokerage + clearing fees

Usage:
  from risk.transaction_costs import total_cost, is_trade_worthwhile
"""

from __future__ import annotations

# Standard Bursa Malaysia retail rates
BROKERAGE_RATE = 0.0010      # 0.10% — typical online broker
STAMP_DUTY_RATE = 0.0010     # 0.10% (RM1 per RM1,000)
STAMP_DUTY_CAP = 200.00      # Max RM200 per contract
CLEARING_RATE = 0.0003       # 0.03%
CLEARING_CAP = 1000.00       # Max RM1,000
SST_RATE = 0.06              # 6% on brokerage + clearing

# Minimums
MIN_BROKERAGE = 8.00         # Minimum brokerage fee (RM)
MIN_CLEARING = 0.50          # Floor clearing fee


def brokerage(trade_value: float, rate: float = BROKERAGE_RATE) -> float:
    """Brokerage fee."""
    fee = trade_value * rate
    return max(fee, MIN_BROKERAGE)


def stamp_duty(trade_value: float) -> float:
    """Stamp duty — RM1 per RM1,000, capped at RM200."""
    duty = trade_value * STAMP_DUTY_RATE
    # Round up to nearest RM1 per RM1,000
    duty = (int(duty) + 1) if duty > int(duty) else duty
    return min(duty, STAMP_DUTY_CAP)


def clearing_fee(trade_value: float) -> float:
    """Clearing fee — 0.03%, capped at RM1,000."""
    fee = trade_value * CLEARING_RATE
    fee = max(fee, MIN_CLEARING)
    return min(fee, CLEARING_CAP)


def sst_tax(brokerage_fee: float, clearing: float) -> float:
    """SST 6% on brokerage + clearing."""
    return (brokerage_fee + clearing) * SST_RATE


def buy_cost(
    trade_value: float,
    brokerage_rate: float = BROKERAGE_RATE,
) -> dict:
    """Total cost to BUY.

    Returns dict with breakdown and total.
    """
    brk = brokerage(trade_value, brokerage_rate)
    stp = stamp_duty(trade_value)
    clr = clearing_fee(trade_value)
    sst = sst_tax(brk, clr)
    total = brk + stp + clr + sst

    return {
        "trade_value": round(trade_value, 2),
        "brokerage": round(brk, 2),
        "stamp_duty": round(stp, 2),
        "clearing": round(clr, 2),
        "sst": round(sst, 2),
        "total_cost": round(total, 2),
        "cost_pct": round(total / trade_value * 100, 4) if trade_value > 0 else 0,
    }


def sell_cost(
    trade_value: float,
    brokerage_rate: float = BROKERAGE_RATE,
) -> dict:
    """Total cost to SELL (same structure as BUY)."""
    # Selling has same fees as buying in Malaysia
    return buy_cost(trade_value, brokerage_rate)


def round_trip_cost(
    trade_value: float,
    brokerage_rate: float = BROKERAGE_RATE,
) -> dict:
    """Total round-trip (buy + sell) cost."""
    buy = buy_cost(trade_value, brokerage_rate)
    sell = sell_cost(trade_value, brokerage_rate)

    total = buy["total_cost"] + sell["total_cost"]
    return {
        "trade_value": round(trade_value, 2),
        "buy_cost": buy,
        "sell_cost": sell,
        "total_round_trip": round(total, 2),
        "round_trip_pct": round(total / trade_value * 100, 4) if trade_value > 0 else 0,
        "breakeven_move_pct": round(total / trade_value * 100, 4) if trade_value > 0 else 0,
    }


def is_trade_worthwhile(
    trade_value: float,
    expected_return_pct: float,
    min_net_return_pct: float = 0.005,  # 0.5% minimum net return
    brokerage_rate: float = BROKERAGE_RATE,
) -> tuple[bool, str]:
    """Check if a trade is worthwhile after costs.

    Args:
        trade_value: RM value of trade
        expected_return_pct: Expected return as decimal (e.g., 0.02 = 2%)
        min_net_return_pct: Minimum acceptable net return after costs

    Returns:
        (worthwhile, reason)
    """
    rt = round_trip_cost(trade_value, brokerage_rate)
    cost_pct = rt["round_trip_pct"] / 100  # Convert to decimal
    net_return = expected_return_pct - cost_pct

    if trade_value < 100:
        return False, f"Trade value RM{trade_value:.2f} too small (min RM100)"
    if net_return < min_net_return_pct:
        return False, (
            f"Net return {net_return*100:.2f}% below min {min_net_return_pct*100:.1f}% "
            f"(costs: {cost_pct*100:.2f}%, expected: {expected_return_pct*100:.1f}%)"
        )
    return True, f"Worthwhile — net return {net_return*100:.2f}% after {cost_pct*100:.2f}% costs"


def cost_summary_table(trade_values: list[float]) -> str:
    """Generate a summary table of costs for different trade sizes."""
    lines = [
        f"{'Trade Value':>12s}  {'Brokerage':>10s}  {'Stamp':>8s}  {'Clearing':>8s}  "
        f"{'SST':>6s}  {'Total':>8s}  {'%':>6s}",
        "-" * 80,
    ]
    for val in trade_values:
        c = buy_cost(val)
        lines.append(
            f"RM {val:>9,.0f}  RM {c['brokerage']:>7.2f}  RM {c['stamp_duty']:>5.2f}  "
            f"RM {c['clearing']:>5.2f}  RM {c['sst']:>4.2f}  "
            f"RM {c['total_cost']:>6.2f}  {c['cost_pct']:>5.2f}%"
        )
    return "\n".join(lines)


# ── Main ────────────────────────────────────────────────────────────

def main():
    print(f"\n{'='*60}")
    print("Bursa Malaysia Transaction Cost Model")
    print(f"{'='*60}")
    print(f"  Brokerage: {BROKERAGE_RATE*100:.2f}% (min RM{MIN_BROKERAGE:.0f})")
    print(f"  Stamp Duty: {STAMP_DUTY_RATE*100:.2f}% (cap RM{STAMP_DUTY_CAP:.0f})")
    print(f"  Clearing: {CLEARING_RATE*100:.2f}% (cap RM{CLEARING_CAP:.0f})")
    print(f"  SST: {SST_RATE*100:.0f}% on brokerage + clearing")

    # Cost table for common trade sizes
    trade_values = [1000, 2000, 5000, 10000, 25000, 50000, 100000]
    print(f"\n  One-way BUY costs:")
    print(f"  {cost_summary_table(trade_values).replace(chr(10), chr(10) + '  ')}")

    # Round-trip examples
    print(f"\n  Round-trip examples:")
    for val in [2000, 5000, 10000]:
        rt = round_trip_cost(val)
        print(f"    RM {val:>6,}: round-trip RM{rt['total_round_trip']:.2f} "
              f"({rt['round_trip_pct']:.2f}%) — breakeven at {rt['breakeven_move_pct']:.2f}% move")

    # Worthwhile checks
    print(f"\n  Trade viability checks:")
    for val, exp in [(1000, 0.02), (2000, 0.01), (5000, 0.015), (10000, 0.005)]:
        ok, reason = is_trade_worthwhile(val, exp)
        icon = "✓" if ok else "✗"
        print(f"    {icon} RM{val:,} @ {exp*100:.1f}% expected: {reason}")


if __name__ == "__main__":
    main()
