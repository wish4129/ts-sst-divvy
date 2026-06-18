#!/usr/bin/env python3
"""Batch Kronos forecast runner — runs for all active stocks in the DB.

Uses import-based call instead of subprocess per batch. This enables:
- Shared DB connection pooling across stocks
- Log aggregation (single output stream)
- Structured error propagation

Usage:
  python3 scripts/run_kronos_batch.py              # Run all active stocks
  python3 scripts/run_kronos_batch.py --skip        # Check only, no run
  python3 scripts/run_kronos_batch.py --force       # Run all stocks even those with < 200 price rows
"""
import sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from db import get_db, dict_cursor
from run_kronos_targeted import run_forecast, write_results


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

    force = "--force" in sys.argv

    # Run in batches of 10 to avoid memory issues
    batch_size = 10
    all_results = {}
    total_run = 0
    start = time.time()

    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i + batch_size]
        idx = i // batch_size + 1
        total_batches = (len(tickers) + batch_size - 1) // batch_size
        print(f"\n--- Batch {idx}/{total_batches} ({len(batch)} stocks) ---")
        t0 = time.time()

        # Call the function directly instead of spawning a subprocess
        batch_results = run_forecast(batch, force=force)
        all_results.update(batch_results)

        elapsed = time.time() - t0
        print(f"  Batch completed in {elapsed:.0f}s")
        total_run += len(batch)

    # Write combined results
    output_path = ROOT / 'data' / 'kronos_forecast.json'
    write_results(all_results, output_path=output_path)

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
    print(f"  Stocks with results:    {len(all_results)}")


if __name__ == "__main__":
    main()
