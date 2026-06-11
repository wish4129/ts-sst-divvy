#!/usr/bin/env python3
"""
sync_persona_config_cash.py — One-shot sync of persona_config.cash from user_portfolios.cash.

Ensures persona_config.cash matches user_portfolios.cash for all personas.
Useful as a standalone script or cron job step when portfolio_manager.py
has been run but the in-process sync_persona_config_cash() may have missed
a persona, or after manual DB edits to user_portfolios.cash.

Usage:
    DB_PASSWORD=xxx python3 scripts/sync_persona_config_cash.py

Returns exit code 0 if all cash values match, 1 if any were fixed, 2 on error.
Prints a report of before/after state.
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from db import get_db, dict_cursor


def main() -> int:
    exit_code = 0
    db = get_db()
    cur = dict_cursor(db)

    try:
        # Read current state from both tables
        cur.execute("SELECT persona_id, name, cash FROM persona_config ORDER BY persona_id")
        pc_rows = {r["persona_id"]: r for r in cur.fetchall()}

        cur.execute(
            "SELECT up.persona, up.id AS portfolio_id, up.name, up.cash "
            "FROM user_portfolios up ORDER BY up.persona"
        )
        up_rows = {r["persona"]: r for r in cur.fetchall()}

        print("=== Cash Sync Report ===")
        print(f"{'Persona':<10} {'PC Cash':>10} {'UP Cash':>10} {'Delta':>8} {'Action':<10}")
        print("-" * 50)

        for persona_id in sorted(set(list(pc_rows.keys()) + list(up_rows.keys()))):
            pc: dict | None = pc_rows.get(persona_id)  # type: ignore[assignment]
            up: dict | None = up_rows.get(persona_id)  # type: ignore[assignment]
            pc_cash = float(pc["cash"]) if pc else None
            up_cash = float(up["cash"]) if up else None

            if pc_cash is not None and up_cash is not None:
                if abs(pc_cash - up_cash) < 0.01:
                    action = "OK"
                else:
                    action = "SYNC"
                    exit_code = 1
                    cur.execute(
                        "UPDATE persona_config SET cash = %s, updated_at = NOW() WHERE persona_id = %s",
                        (up_cash, persona_id),
                    )
            elif pc_cash is None and up_cash is not None:
                action = "MISSING_PC"
                exit_code = 1
                print(
                    f"  WARNING: persona_config row missing for persona_id='{persona_id}' — "
                    f"cannot sync cash={up_cash} from user_portfolios"
                )
            elif pc_cash is not None and up_cash is None:
                action = "NO_PORTFOLIO"
                print(
                    f"  Note: persona '{pc['name']}' ({persona_id}) has no user_portfolios row"
                )
            else:
                action = "NO_DATA"

            delta = (up_cash or 0) - (pc_cash or 0) if (pc_cash is not None and up_cash is not None) else 0
            print(
                f"{persona_id:<10} "
                f"{pc_cash if pc_cash is not None else 'N/A':>10} "
                f"{up_cash if up_cash is not None else 'N/A':>10} "
                f"{delta:>+8.2f} "
                f"{action:<10}"
            )

        db.commit()

        # Verification
        cur.execute("SELECT persona_id, name, cash FROM persona_config ORDER BY persona_id")
        print("\n=== Post-sync verification ===")
        for r in cur.fetchall():
            print(f"  {r['persona_id']}: {r['name']} — cash={r['cash']}")

        if exit_code == 0:
            print("\n✓ All persona_config.cash values match user_portfolios.cash. No changes needed.")
        else:
            print(f"\n⚠ Some values were synced. Re-run to confirm zero deltas.")

        db.close()
        return exit_code

    except Exception as e:
        db.rollback()
        db.close()
        print(f"ERROR: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
