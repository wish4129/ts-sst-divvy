#!/usr/bin/env python3
"""Stock screener with deduplication against watchlist and bursa_universe.

Reads candidates from screener_results.json or scrapes from KLSE Screener.
Checks against stocks table (watchlist) and bursa_universe table.
Flags duplicates, inserts new candidates into screener_candidates table.

Usage:
    .venv/bin/python3 scripts/screener.py              # from screener_results.json
    .venv/bin/python3 scripts/screener.py --json-only  # just update JSON, skip DB
"""

import json
import sys
import os
from datetime import datetime, timezone
from pathlib import Path

# Add scripts dir to path for db import
sys.path.insert(0, str(Path(__file__).parent))
from db import get_db
from persona_db import SHORT_TO_TICKER, TICKER_TO_SHORT

def resolve_ticker(code: str) -> str:
    """Convert short code to ticker (e.g., MAGNI → 7087.KL)."""
    return SHORT_TO_TICKER.get(code.upper(), code.upper() + '.KL')


def deduplicate_candidates(candidates: list, db_conn) -> list:
    """Check each candidate against stocks (watchlist) and bursa_universe.
    
    Returns candidates enriched with dedup_status:
      - 'in_watchlist': already in stocks table (active/revisit)
      - 'in_universe': in bursa_universe but not watchlist
      - 'new': not in either table
    """
    cur = db_conn.cursor()
    
    # Get all watchlist tickers
    cur.execute("SELECT id FROM stocks WHERE status != 'removed'")
    watchlist_tickers = {r[0] for r in cur.fetchall()}
    
    # Get all bursa_universe stock codes
    cur.execute("SELECT stock_code FROM bursa_universe")
    universe_codes = {r[0] for r in cur.fetchall()}
    
    enriched = []
    for c in candidates:
        code = c['code'].upper()
        ticker = resolve_ticker(code)
        
        if ticker in watchlist_tickers or code in watchlist_tickers:
            c['dedup_status'] = 'in_watchlist'
        elif ticker in universe_codes or (ticker.replace('.KL', '') in universe_codes):
            c['dedup_status'] = 'in_universe'
        else:
            c['dedup_status'] = 'new'
        
        c['ticker'] = ticker
        enriched.append(c)
    
    return enriched


def insert_candidates(candidates: list, db_conn) -> int:
    """Insert new/non-duplicate candidates into screener_candidates table.
    Returns number inserted."""
    cur = db_conn.cursor()
    inserted = 0
    
    for c in candidates:
        if c['dedup_status'] == 'in_watchlist':
            continue  # skip duplicates
        
        ticker = c.get('ticker', resolve_ticker(c['code']))
        score = c.get('score', {}).get('composite', 0)
        
        # Check if already in screener_candidates
        cur.execute(
            "SELECT id FROM screener_candidates WHERE stock_code = %s",
            (ticker,)
        )
        if cur.fetchone():
            continue  # already exists in screener
        
        cur.execute(
            """INSERT INTO screener_candidates 
               (stock_code, stock_name, pe_ratio, dividend_yield, roe, composite_score)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (
                ticker,
                c.get('name', ''),
                c.get('pe'),
                c.get('dividendYield'),
                c.get('roe'),
                score,
            )
        )
        inserted += 1
    
    db_conn.commit()
    return inserted


def main():
    json_only = '--json-only' in sys.argv
    
    # Load candidates
    json_path = Path(__file__).parent.parent / 'data' / 'screener_results.json'
    if not json_path.exists():
        print(f'No screener_results.json found at {json_path}')
        return
    
    with open(json_path) as f:
        data = json.load(f)
    
    candidates = data.get('new_candidates', [])
    if not candidates:
        print('No candidates in screener_results.json')
        return
    
    print(f'Loaded {len(candidates)} candidates from screener_results.json')
    
    # Deduplicate
    db = get_db()
    enriched = deduplicate_candidates(candidates, db)
    
    # Report
    in_watchlist = [c for c in enriched if c['dedup_status'] == 'in_watchlist']
    in_universe = [c for c in enriched if c['dedup_status'] == 'in_universe']
    new_candidates = [c for c in enriched if c['dedup_status'] == 'new']
    
    print(f'\n=== Deduplication Results ===')
    print(f'  In watchlist (skip):  {len(in_watchlist)}')
    for c in in_watchlist:
        print(f'    ✗ {c["code"]:10s} {c["name"]:30s} → already in watchlist ({c["ticker"]})')
    
    print(f'  In universe (flag):   {len(in_universe)}')
    for c in in_universe:
        print(f'    ◉ {c["code"]:10s} {c["name"]:30s} → in bursa_universe, not watchlist')
    
    print(f'  New candidates:       {len(new_candidates)}')
    for c in new_candidates:
        print(f'    ✓ {c["code"]:10s} {c["name"]:30s} → score={c.get("score",{}).get("composite","?")}')
    
    # Update JSON with dedup status
    data['new_candidates'] = enriched
    data['dedup_checked_at'] = datetime.now(timezone.utc).isoformat()
    data['dedup_summary'] = {
        'total': len(enriched),
        'in_watchlist': len(in_watchlist),
        'in_universe': len(in_universe),
        'new': len(new_candidates),
    }
    
    with open(json_path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f'\nUpdated {json_path} with dedup flags')
    
    if not json_only:
        # Insert new candidates into DB
        to_insert = new_candidates + in_universe
        inserted = insert_candidates(to_insert, db)
        print(f'Inserted {inserted} candidates into screener_candidates table')
    
    db.close()
    print('\nDone.')


if __name__ == '__main__':
    main()
