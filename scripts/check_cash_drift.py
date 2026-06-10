#!/usr/bin/env python3
"""Health check: detect cash drift between persona_config and user_portfolios.

Both tables track cash, but only user_portfolios gets updated by
portfolio_manager runs. persona_config.cash can go stale if the
auto-sync in portfolio_manager.sync_persona_config_cash() fails silently.

Run as part of cron maintenance or pre-battle checks.

Exit code: 0 (no drift) | 1 (drift detected)
"""
import json
import sys
from db import get_db

THRESHOLD = 1.0


def check_drift():
    db = get_db()
    cur = db.cursor()

    cur.execute("""
        SELECT pc.persona_id, pc.cash AS config_cash, up.cash AS portfolio_cash,
               ABS(pc.cash - up.cash) AS drift
        FROM persona_config pc
        JOIN user_portfolios up ON pc.persona_id = up.persona
        WHERE ABS(pc.cash - up.cash) > %s
        ORDER BY drift DESC
    """, (THRESHOLD,))

    rows = cur.fetchall()
    cur.close()
    db.close()

    if not rows:
        print("OK — No cash drift detected (threshold = RM%.2f)" % THRESHOLD)
        return 0

    print("CASH DRIFT DETECTED (threshold = RM%.2f):" % THRESHOLD)
    print("")
    print(f"{'Persona':<12} {'Config Cash':>12} {'Portfolio Cash':>14} {'Drift':>8}")
    print("-" * 48)
    for r in rows:
        print(f"{r[0]:<12} {float(r[1]):>12.2f} {float(r[2]):>14.2f} {float(r[3]):>8.2f}")
    print("")
    print("Run: UPDATE persona_config SET cash = up.cash, updated_at = NOW()")
    print("     FROM user_portfolios up")
    print("     WHERE persona_config.persona_id = up.persona")
    print("     AND ABS(persona_config.cash - up.cash) > 1.0;")
    return 1


if __name__ == "__main__":
    sys.exit(check_drift())
