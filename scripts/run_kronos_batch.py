#!/usr/bin/env python3
"""Modified run_kronos_batch.py with pre-check — skip if file already matches DB.

The key idea: before running Kronos (which is slow — ~1.5 min per stock * 149 = 3.5+ hours),
check if the existing kronos_forecast.json file already has entries for all active stocks
with recent forecast dates. If it does, skip the run entirely.
"""

import sys, json, time
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


def pre_check_file_matches_db():
    """
    Compare the existing kronos_forecast.json file against the DB.
    
    Returns: 
        (match: bool, message: str)
        match=True means the file already reflects all active stocks — skip the run.
    """
    json_path = ROOT / 'data' / 'kronos_forecast.json'
    
    if not json_path.exists():
        return False, "No existing kronos_forecast.json file — must regenerate."
    
    # Load existing file
    try:
        with open(json_path) as f:
            existing = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        return False, f"Cannot read existing JSON ({e}) — will regenerate."
    
    existing_stocks = len(existing)
    if existing_stocks == 0:
        return False, "Existing kronos_forecast.json is empty — must regenerate."
    
    # Get active stock count
    active = get_active_tickers()
    active_count = len(active)
    
    # The JSON file keys are company names (e.g. "7-ELEVEN MALAYSIA HOLDINGS BERHAD"),
    # but each entry has a "ticker" field (e.g. "5250.KL").
    # Compare using the ticker field, not the keys.
    file_tickers = set()
    for name, entry in existing.items():
        if isinstance(entry, dict) and "ticker" in entry:
            file_tickers.add(entry["ticker"])
    
    missing = set(active) - file_tickers
    
    if missing:
        return False, f"File has entries for {len(file_tickers)} stocks but DB has {active_count} active — missing {len(missing)} (e.g. {', '.join(sorted(missing)[:5])}{'...' if len(missing) > 5 else ''})"
    
    # Check DB freshness: does the DB already have recent forecasts for all active stocks?
    db = get_db()
    try:
        cur = dict_cursor(db)
        cur.execute(
            "SELECT COUNT(DISTINCT stock_id) FROM kronos_forecasts "
            "WHERE generated_at > NOW() - INTERVAL '24 hours'"
        )
        row = cur.fetchone()
        db_fresh = row['count'] if row else 0
        cur.close()
    finally:
        db.close()
    
    match_pct = (len(file_tickers) / active_count * 100) if active_count > 0 else 0
    msg = (
        f"File matches DB: {len(file_tickers)} entries for {active_count} active stocks "
        f"({match_pct:.0f}% coverage). "
        f"DB fresh (last 24h): {db_fresh} stocks."
    )
    
    # Decide: skip if coverage >= 90% AND DB has at least 50% fresh
    threshold = 0.9
    if match_pct / 100 >= threshold and db_fresh >= active_count * 0.5:
        return True, msg + " SUFFICIENT COVERAGE — skipping regeneration."
    else:
        return False, msg + " BELOW THRESHOLD — regenerating."


def main():
    tickers = get_active_tickers()
    print(f"Active stocks in DB: {len(tickers)}")
    
    # Pre-check: does the JSON file already match the DB?
    skip, msg = pre_check_file_matches_db()
    print(f"\n=== Pre-Check ===")
    print(f"  {msg}")
    
    if skip:
        print(f"\n[SKIP] kronos_forecast.json is current. No regeneration needed.")
        return
    
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
