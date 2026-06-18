#!/usr/bin/env python3
"""Batch Kronos forecast runner — runs for all active stocks in the DB.
Used by: t_fd512729 — [PANGU] Refresh Kronos forecasts from DB for all 77 stocks

Usage:
  python3 scripts/run_kronos_batch.py              # Run all 77 stocks
  python3 scripts/run_kronos_batch.py --skip        # Check only, no run
  python3 scripts/run_kronos_batch.py --force       # Run all stocks even those with < 200 price rows
"""
import subprocess, sys, time, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from db import get_db, dict_cursor


def get_active_tickers():
    db = get_db()
    cur = dict_cursor(db)
    cur.execute("SELECT id FROM stocks WHERE status NOT IN ('removed', 'data_missing') ORDER BY id")
    ids = [r['id'] for r in cur.fetchall()]
    cur.close()
    db.close()
    return ids


def check_forecast_count(db):
    cur = db.cursor()
    cur.execute(
        "SELECT COUNT(DISTINCT stock_id) FROM kronos_forecasts "
        "WHERE generated_at > NOW() - INTERVAL '1 hour'"
    )
    count = cur.fetchone()[0]
    cur.close()
    return count


def main():
    tickers = get_active_tickers()
    print(f"Active stocks in DB: {len(tickers)}")

    # Check current state
    db = get_db()
    before = check_forecast_count(db)
    db.close()
    print(f"Fresh forecasts (last hour) before run: {before}")

    if "--skip" in sys.argv:
        print("SKIP: dry-run mode, exiting.")
        return

    # Run in batches of 10 to avoid memory issues
    batch_size = 10
    total_run = 0
    start = time.time()

    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i + batch_size]
        print(f"\n--- Batch {i // batch_size + 1}/{(len(tickers) + batch_size - 1) // batch_size} ({len(batch)} stocks) ---")
        t0 = time.time()
        cmd = [sys.executable, str(ROOT / "scripts" / "run_kronos_targeted.py")]
        if "--force" in sys.argv:
            cmd.append("--force")
        cmd += batch
        result = subprocess.run(
            cmd,
            capture_output=True, text=True, timeout=600,
            cwd=str(ROOT)
        )
        elapsed = time.time() - t0
        print(result.stdout[-500:] if result.stdout else "")
        if result.returncode != 0:
            print(f"  STDERR: {result.stderr[-200:]}")
        print(f"  Batch completed in {elapsed:.0f}s")
        total_run += len(batch)

    # Final verification
    db = get_db()
    after = check_forecast_count(db)
    db.close()
    total_elapsed = time.time() - start
    print(f"\n{'='*50}")
    print(f"BATCH RUN COMPLETE")
    print(f"  Stocks processed: {total_run}")
    print(f"  Total time: {total_elapsed:.0f}s ({total_elapsed/60:.1f}m)")
    print(f"  Fresh forecasts before: {before}")
    print(f"  Fresh forecasts after:  {after}")


if __name__ == "__main__":
    main()
