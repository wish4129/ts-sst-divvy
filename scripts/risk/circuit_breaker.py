#!/usr/bin/env python3
"""Maximum drawdown circuit breaker — freeze new entries when losses exceed threshold.

Per-persona drawdown tracking with persistent peak values. When a persona's
portfolio drops below the threshold (default -25% from peak), the circuit
breaker trips and blocks new BUY entries until the drawdown recovers.

SELL and SELL_ALL orders always execute (stop losses, take profits, trims).
Only BUY and rebalance-add orders are blocked during a trip.

State persisted to data/circuit_breakers.json with per-persona peaks
updated on each run.

Usage:
  cd ~/xiongit/divvy && .venv/bin/python3 scripts/risk/circuit_breaker.py
  cd ~/xiongit/divvy && .venv/bin/python3 scripts/risk/circuit_breaker.py --threshold 0.20
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db import get_db
from persona_db import get_all_stocks_dict

ROOT = Path(__file__).resolve().parent.parent.parent
MALAYSIA_TZ = timezone(timedelta(hours=8))
STATE_PATH = ROOT / "data" / "circuit_breakers.json"

# Default thresholds per persona
DEFAULT_THRESHOLD = 0.25  # 25% drawdown triggers breaker
PERSONA_THRESHOLDS = {
    "ares": 0.25,     # Aggressive — higher tolerance before freeze
    "demeter": 0.20,  # Conservative — freeze earlier
    "athena": 0.22,   # Balanced
}


def _load_state() -> dict:
    """Load circuit breaker state from disk."""
    if not STATE_PATH.exists():
        return {"personas": {}}
    try:
        return json.loads(STATE_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return {"personas": {}}


def _save_state(state: dict) -> None:
    """Persist circuit breaker state."""
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2))


def get_peak_value(persona_id: str) -> Optional[float]:
    """Get the all-time peak portfolio value for a persona."""
    state = _load_state()
    pid_state = state.get("personas", {}).get(persona_id, {})
    return pid_state.get("peak_value")


def update_peak(persona_id: str, current_value: float) -> float:
    """Update peak value if current exceeds it. Returns the (possibly new) peak."""
    state = _load_state()
    pid_state = state.get("personas", {}).get(persona_id, {})

    current_peak = pid_state.get("peak_value", 0)
    if current_value > current_peak:
        pid_state["peak_value"] = current_value
        pid_state["peak_date"] = datetime.now(MALAYSIA_TZ).isoformat()
        pid_state.setdefault("tripped_count", 0)
        pid_state.setdefault("tripped_at", None)
        pid_state["last_updated"] = datetime.now(MALAYSIA_TZ).isoformat()

    state.setdefault("personas", {})[persona_id] = pid_state
    _save_state(state)
    return max(current_peak, current_value)


def check_circuit_breaker(
    persona_id: str,
    current_value: float,
    threshold: Optional[float] = None,
) -> Tuple[bool, float, Dict]:
    """Check if circuit breaker is tripped.

    Args:
        persona_id: e.g. 'ares', 'demeter', 'athena'
        current_value: Current total portfolio value
        threshold: Drawdown threshold as decimal (default: persona-specific, fallback 0.25)

    Returns:
        (tripped, drawdown_pct, state_info)
        tripped: True if breaker is active (block new BUYs)
        drawdown_pct: Current drawdown from peak as decimal (negative)
        state_info: Full state dict for this persona
    """
    if threshold is None:
        threshold = PERSONA_THRESHOLDS.get(persona_id, DEFAULT_THRESHOLD)

    state = _load_state()
    pid_state = state.get("personas", {}).get(persona_id, {})
    peak = pid_state.get("peak_value", current_value)

    if peak <= 0 or current_value <= 0:
        return False, 0.0, pid_state

    drawdown = (current_value - peak) / peak

    # Trip if drawdown exceeds threshold
    tripped = drawdown <= -threshold

    # If tripped, record it
    if tripped and not pid_state.get("tripped", False):
        pid_state["tripped"] = True
        pid_state["tripped_count"] = pid_state.get("tripped_count", 0) + 1
        pid_state["tripped_at"] = datetime.now(MALAYSIA_TZ).isoformat()
        pid_state["tripped_from_peak"] = peak
        pid_state["tripped_from_value"] = current_value

    # If recovered (was tripped, now above threshold)
    if not tripped and pid_state.get("tripped", False):
        pid_state["tripped"] = False
        pid_state["recovered_at"] = datetime.now(MALAYSIA_TZ).isoformat()
        pid_state["recovered_from_value"] = current_value

    pid_state["last_checked"] = datetime.now(MALAYSIA_TZ).isoformat()
    pid_state["current_drawdown"] = round(drawdown, 4)

    state.setdefault("personas", {})[persona_id] = pid_state
    _save_state(state)

    return tripped, drawdown, pid_state


def is_buy_blocked(persona_id: str, current_value: float) -> Tuple[bool, str]:
    """Check if BUY orders should be blocked for this persona.

    Returns:
        (blocked, reason)
    """
    tripped, drawdown, state = check_circuit_breaker(persona_id, current_value)

    if not tripped:
        return False, ""

    drawdown_pct = abs(drawdown) * 100
    threshold = PERSONA_THRESHOLDS.get(persona_id, DEFAULT_THRESHOLD) * 100
    trips = state.get("tripped_count", 0)
    peak = state.get("peak_value", current_value)

    reason = (
        f"Circuit breaker TRIPPED: {drawdown_pct:.1f}% drawdown "
        f"(peak RM{peak:,.2f} → RM{current_value:,.2f}, "
        f"threshold {threshold:.0f}%). "
        f"Trip #{trips}. Only SELL orders allowed."
    )
    return True, reason


def get_circuit_breaker_summary(persona_id: str) -> Dict:
    """Get human-readable circuit breaker status."""
    state = _load_state()
    pid_state = state.get("personas", {}).get(persona_id, {})

    peak = pid_state.get("peak_value", 0)
    tripped = pid_state.get("tripped", False)
    drawdown = pid_state.get("current_drawdown", 0)
    trips = pid_state.get("tripped_count", 0)
    threshold = PERSONA_THRESHOLDS.get(persona_id, DEFAULT_THRESHOLD)

    # Derive status
    if tripped:
        status = "🔴 TRIPPED"
    elif drawdown <= -threshold * 0.5:
        status = "🟡 WARNING"  # Within 50% of threshold
    else:
        status = "🟢 OK"

    return {
        "persona": persona_id,
        "status": status,
        "tripped": tripped,
        "peak_value": round(peak, 2) if peak else None,
        "current_drawdown_pct": round(drawdown * 100, 2),
        "threshold_pct": round(threshold * 100, 0),
        "trip_count": trips,
        "tripped_at": pid_state.get("tripped_at"),
        "recovered_at": pid_state.get("recovered_at"),
        "peak_date": pid_state.get("peak_date"),
    }


def load_portfolio_values_from_db() -> Dict[str, float]:
    """Get current total portfolio values from latest snapshots."""
    db = get_db()
    cur = db.cursor()
    values = {}

    cur.execute(
        """SELECT DISTINCT ON (up.persona) up.persona, ps.total_value
           FROM portfolio_snapshots ps
           JOIN user_portfolios up ON up.id = ps.portfolio_id
           ORDER BY up.persona, ps.snapshot_at DESC"""
    )
    for row in cur.fetchall():
        values[row[0]] = float(row[1])

    cur.close()
    db.close()
    return values


# ── Main ────────────────────────────────────────────────────────────

def run_circuit_breaker_check(
    thresholds: Optional[Dict[str, float]] = None,
) -> Dict:
    """Check circuit breakers for all personas.

    Returns:
        Dict with per-persona status.
    """
    print(f"\n{'='*60}")
    print("Circuit Breaker Status Check")
    print(f"{'='*60}")

    # Load current portfolio values
    portfolio_values = load_portfolio_values_from_db()

    if not portfolio_values:
        print("  No portfolio snapshots found — initializing peaks from current state")
        # Try loading from persona_config
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT persona_id, initial_capital FROM persona_config")
        for row in cur.fetchall():
            pid = row[0]
            cap = float(row[1])
            portfolio_values[pid] = cap
        cur.close()
        db.close()

    results = {}
    for pid in ["ares", "demeter", "athena"]:
        current = portfolio_values.get(pid, 10000.0)
        threshold = (thresholds or {}).get(pid, PERSONA_THRESHOLDS.get(pid, DEFAULT_THRESHOLD))

        # Update peak (also initializes if never run)
        peak = update_peak(pid, current)

        # Check breaker
        tripped, drawdown, state = check_circuit_breaker(pid, current, threshold)

        summary = get_circuit_breaker_summary(pid)
        results[pid] = summary

        # Print status
        if tripped:
            blocked, reason = is_buy_blocked(pid, current)
            print(f"\n  [{pid.upper()}] {summary['status']}")
            print(f"    {reason}")
        elif summary["status"] == "🟡 WARNING":
            print(f"  [{pid.upper()}] {summary['status']}  "
                  f"Drawdown: {summary['current_drawdown_pct']:+.1f}%  "
                  f"Peak: RM{summary['peak_value']:,.2f}  "
                  f"Threshold: {summary['threshold_pct']:.0f}%")
        else:
            print(f"  [{pid.upper()}] {summary['status']}  "
                  f"Drawdown: {summary['current_drawdown_pct']:+.1f}%  "
                  f"Peak: RM{summary['peak_value']:,.2f}  "
                  f"Trips: {summary['trip_count']}")

    # Check if any are tripped
    any_tripped = any(r["tripped"] for r in results.values())
    if any_tripped:
        print(f"\n  ⚠️  CIRCUIT BREAKER(S) TRIPPED — BUY orders blocked")
    else:
        print(f"\n  ✓ All circuit breakers normal — full trading permitted")

    return results


def main():
    thresholds = {}
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        arg = args[i]
        if arg.startswith("--threshold="):
            t = float(arg.split("=", 1)[1])
            thresholds = {p: t for p in ["ares", "demeter", "athena"]}
        elif arg == "--threshold" and i + 1 < len(args):
            i += 1; t = float(args[i])
            thresholds = {p: t for p in ["ares", "demeter", "athena"]}
        elif arg == "--reset":
            # Reset all circuit breakers
            STATE_PATH.write_text(json.dumps({"personas": {}}, indent=2))
            print("Circuit breakers reset.")
            return
        i += 1

    results = run_circuit_breaker_check(thresholds if thresholds else None)

    # Save status report
    output_path = ROOT / "data" / "circuit_breaker_status.json"
    output = {
        "checked_at": datetime.now(MALAYSIA_TZ).isoformat(),
        "personas": results,
        "any_tripped": any(r["tripped"] for r in results.values()),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2))
    print(f"\n  ✓ Status saved to {output_path}")


if __name__ == "__main__":
    main()
