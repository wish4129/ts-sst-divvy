#!/usr/bin/env python3
"""
Monitor new Bursa Malaysia stock listings (IPOs).

Scrapes the authoritative SMFA stock code table daily and compares
against the bursa_universe table. Detects new listings before they're
manually added to the universe.

Run: python3 scripts/monitor_new_listings.py
Schedule: daily 8am MYT (via hermes cron)

Deliverable:
  - Detects new stock codes not in bursa_universe
  - Inserts them with placeholder data
  - Prints alert output for cron delivery
"""
import sys
import csv
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, 'scripts')
from db import get_db, dict_cursor

SMFA_URL = "https://raw.githubusercontent.com/kj-lai/SMFA/master/stock_code_table.csv"
# Known non-stock codes to skip (ETFs, indices, bonds, etc.)
SKIP_PREFIXES = ('0',)  # 0xxx = preference shares / bonds usually
# Minimum code length for stocks (Malaysia stock codes are 4 digits)
MIN_CODE_LEN = 4
# DB table name — verified against live schema (2026-06-18)
BURSA_TABLE = 'bursa_universe'
CODE_COL = 'stock_code'  # actual column, not 'code' as schema.ts suggests


def fetch_smfa_universe():
    """Fetch the SMFA stock code table, return {code: name} dict."""
    print(f"[{datetime.now(timezone.utc).isoformat()}] Fetching SMFA stock code table...")
    req = urllib.request.Request(
        SMFA_URL,
        headers={'User-Agent': 'DivvyMonitor/1.0'}
    )
    resp = urllib.request.urlopen(req, timeout=60)
    content = resp.read().decode('utf-8')

    reader = csv.DictReader(content.splitlines())
    stocks = {}
    for row in reader:
        code = row.get('code', '').strip()
        name = row.get('name', '').strip().replace('+', ' ')
        if not code or not name:
            continue
        # Skip non-stock entries
        if len(code) < MIN_CODE_LEN:
            continue
        if any(code.startswith(p) for p in SKIP_PREFIXES):
            continue
        stocks[code] = name

    print(f"  Found {len(stocks)} stocks in SMFA table")
    return stocks


def get_existing_codes(conn):
    """Return set of stock codes already in bursa_universe (normalized, no .KL suffix)."""
    with dict_cursor(conn) as cur:
        cur.execute(f"SELECT {CODE_COL} FROM {BURSA_TABLE}")
        codes = set()
        for row in cur.fetchall():
            code = row[CODE_COL]
            # Normalize: strip .KL suffix for comparison with SMFA bare codes
            if code.endswith('.KL'):
                code = code[:-3]
            codes.add(code)
        return codes


def get_existing_stocks(conn):
    """Return set of stock codes (stripped of .KL) in the main stocks table."""
    with dict_cursor(conn) as cur:
        cur.execute("SELECT id FROM stocks WHERE status = 'active'")
        return {row['id'].replace('.KL', '') for row in cur.fetchall()}


def infer_market(code):
    """Infer Bursa market from stock code prefix."""
    code_i = int(code)
    if 1 <= code_i <= 1999:
        return 'Main Market'
    elif 5000 <= code_i <= 5999:
        return 'Main Market'  # REITs, financials
    elif 7000 <= code_i <= 7999:
        return 'ACE Market'
    elif 2000 <= code_i <= 2999:
        return 'LEAP Market'
    elif 3000 <= code_i <= 3999:
        return 'LEAP Market'
    elif 8000 <= code_i <= 8999:
        return 'ACE Market'  # Technology
    elif 9000 <= code_i <= 9999:
        return 'Main Market'  # Closed-end funds
    elif 6000 <= code_i <= 6999:
        return 'Main Market'  # ETFs
    elif 4000 <= code_i <= 4999:
        return 'ACE Market'
    else:
        return 'Unknown'


def main():
    try:
        smfa = fetch_smfa_universe()
    except Exception as e:
        print(f"ERROR: Failed to fetch SMFA table: {e}")
        sys.exit(1)

    conn = get_db()
    try:
        existing = get_existing_codes(conn)
        existing_stocks = get_existing_stocks(conn)

        new_codes = []
        for code, name in sorted(smfa.items()):
            if code not in existing:
                new_codes.append((code, name))

        if not new_codes:
            print(f"\n✅ No new listings detected. bursa_universe has {len(existing)} codes.")
            print(f"   SMFA has {len(smfa)} codes — universe is up to date.")
            return

        print(f"\n⚠️  Found {len(new_codes)} potential new listing(s):")
        for code, name in new_codes:
            print(f"  {code}: {name}")

        # Insert new codes
        insert_success = 0
        insert_fail = 0
        with conn.cursor() as cur:
            for code, name in new_codes:
                try:
                    cur.execute(f"""
                        INSERT INTO {BURSA_TABLE} ({CODE_COL}, name, added_at)
                        VALUES (%s, %s, NOW())
                        ON CONFLICT ({CODE_COL}) DO NOTHING
                    """, (code, name))
                    insert_success += 1
                except Exception as e:
                    print(f"  ERROR inserting {code}: {e}")
                    insert_fail += 1
            conn.commit()

        print(f"\n✅ Inserted {insert_success} new codes, {insert_fail} errors")

    except Exception as e:
        conn.rollback()
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
