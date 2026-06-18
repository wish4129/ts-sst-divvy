#!/usr/bin/env python3
"""Refill the stock_prices table from yfinance for all active stocks.

The stock_prices table currently has 0 rows for all stocks, which breaks the
Kronos pre-filter in run_kronos_targeted.py (skips stocks with <200 rows).

Usage:
    cd ~/xionGit/divvy
    python3 scripts/refill_stock_prices.py
    python3 scripts/refill_stock_prices.py --dry-run   # preview only
    python3 scripts/refill_stock_prices.py --ticker 1155.KL  # single ticker

Schema:
    stock_prices(stock_id TEXT, date DATE, open NUMERIC, high NUMERIC,
                 low NUMERIC, close NUMERIC, volume BIGINT)
    PK: (stock_id, date) with ON CONFLICT DO NOTHING

This script:
1. Fetches active stocks from the `stocks` table (status NOT IN 'removed','data_missing')
2. Downloads 2 years of daily OHLCV data from yfinance per stock
3. Batches INSERTs into Supabase stock_prices table
4. Reports progress and summary
"""

import sys
import time
from pathlib import Path

import yfinance as yf
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from db import get_db, dict_cursor

# ── Configuration ─────────────────────────────────────────────────────────────

FETCH_PERIOD = "2y"       # 2 years of daily data (~500 trading days >> 200 threshold)
INSERT_BATCH = 50         # rows per INSERT statement
YFINANCE_DELAY = 1.0      # seconds between yfinance calls to avoid rate limiting

# ── Helpers ───────────────────────────────────────────────────────────────────


def get_active_ids() -> list[str]:
    """Return all stock IDs that should have price history."""
    db = get_db()
    cur = dict_cursor(db)
    cur.execute(
        "SELECT id FROM stocks WHERE status NOT IN ('removed', 'data_missing') ORDER BY id"
    )
    ids = [r["id"] for r in cur.fetchall()]
    cur.close()
    db.close()
    return ids


def fetch_prices(ticker_id: str) -> pd.DataFrame | None:
    """Fetch up to FETCH_PERIOD of daily OHLCV from yfinance.

    Returns a DataFrame with columns: date, open, high, low, close, volume
    or None on failure.
    """
    try:
        t = yf.Ticker(ticker_id)
        hist = t.history(period=FETCH_PERIOD)
        if hist.empty:
            print(f"  ⚠  {ticker_id}: no data returned by yfinance")
            return None

        records = []
        for idx, row in hist.iterrows():
            records.append({
                "stock_id": ticker_id,
                "date": idx.strftime("%Y-%m-%d"),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": int(row["Volume"]) if pd.notna(row["Volume"]) else 0,
            })
        return pd.DataFrame(records)
    except Exception as e:
        print(f"  ✗  {ticker_id}: error — {e}")
        return None


def batch_insert(df: pd.DataFrame, conn, cur, ticker: str) -> int:
    """Insert price rows in batches. Returns count of rows inserted."""
    if df is None or df.empty:
        return 0

    total = 0
    for start in range(0, len(df), INSERT_BATCH):
        batch = df.iloc[start : start + INSERT_BATCH]
        values = []
        for _, row in batch.iterrows():
            values.append(
                f"('{row['stock_id']}', '{row['date']}', "
                f"{row['open']}, {row['high']}, {row['low']}, "
                f"{row['close']}, {row['volume']})"
            )
        if not values:
            continue

        sql = (
            "INSERT INTO stock_prices (stock_id, date, open, high, low, close, volume) "
            "VALUES " + ",".join(values) + " "
            "ON CONFLICT (stock_id, date) DO NOTHING"
        )
        try:
            cur.execute(sql)
            conn.commit()
            total += cur.rowcount
        except Exception as e:
            conn.rollback()
            print(f"  ✗  {ticker}: batch insert error — {e}")
            return total

    return total


def check_existing_counts(conn) -> dict[str, int]:
    """Return {stock_id: row_count} for all stocks currently in stock_prices."""
    cur = dict_cursor(conn)
    cur.execute(
        "SELECT stock_id, COUNT(*)::int AS cnt FROM stock_prices GROUP BY stock_id"
    )
    result = {r["stock_id"]: r["cnt"] for r in cur.fetchall()}
    cur.close()
    return result


# ── Main ──────────────────────────────────────────────────────────────────────


def main():
    dry_run = "--dry-run" in sys.argv
    single_ticker = None
    for arg in sys.argv[1:]:
        if arg.startswith("--ticker="):
            single_ticker = arg.split("=", 1)[1]
        elif arg == "--ticker" and len(sys.argv) > sys.argv.index(arg) + 1:
            idx = sys.argv.index(arg)
            single_ticker = sys.argv[idx + 1]

    print("=" * 60)
    print("  stock_prices Refill Script")
    print("=" * 60)
    print()

    if dry_run:
        print("  [DRY RUN] No data will be written\n")

    # 1. Get the target stock IDs
    all_ids = get_active_ids()
    target_ids = [single_ticker] if single_ticker else all_ids

    print(f"  Target stocks: {len(target_ids)}")
    if len(target_ids) <= 20:
        for sid in target_ids:
            print(f"    • {sid}")
    print()

    # 2. Check current state
    if not dry_run:
        conn = get_db()
        existing = check_existing_counts(conn)
        conn.close()
        already_full = {k for k, v in existing.items() if v >= 400}  # ~2y of trading days
        need_refill = [sid for sid in target_ids if sid not in already_full]
        partial = {k: v for k, v in existing.items() if v < 400 and v > 0}

        print(f"  Already have ≥400 rows: {len(already_full)} stocks")
        if partial:
            print(f"  Partial counts (<400): {len(partial)} stocks")
            for sid, cnt in list(partial.items())[:5]:
                print(f"    • {sid}: {cnt} rows")

        target_ids = need_refill
        print(f"  Need refill: {len(target_ids)} stocks\n")
    else:
        target_ids = target_ids  # show all in dry run
        print("  (dry run — will show all targets)\n")

    if not target_ids:
        print("  ✓ All stocks already have sufficient price history.")
        return

    if dry_run:
        print("  [DRY RUN] Would fetch and insert for:", len(target_ids), "stocks")
        for sid in target_ids[:5]:
            print(f"    • {sid}")
        if len(target_ids) > 5:
            print(f"    ... and {len(target_ids) - 5} more")
        print("\n  [DRY RUN] No data written. Exiting.")
        return

    # 3. Process each stock
    conn = get_db()
    cur = dict_cursor(conn)

    total_inserted = 0
    total_failed = 0
    total_skipped = 0
    started = time.time()

    print(f"  Fetching {FETCH_PERIOD} of price history for {len(target_ids)} stocks...\n")

    for i, sid in enumerate(target_ids, 1):
        print(f"  [{i}/{len(target_ids)}] {sid}...", end=" ", flush=True)

        df = fetch_prices(sid)
        if df is None:
            total_failed += 1
            continue

        inserted = batch_insert(df, conn, cur, sid)
        if inserted > 0:
            print(f"✓ {inserted} rows inserted (total {len(df)} fetched)")
            total_inserted += inserted
        else:
            print(f"  — 0 new rows (all already present in DB)")
            total_skipped += 1

        time.sleep(YFINANCE_DELAY)

    cur.close()
    conn.close()

    # 4. Summary
    elapsed = time.time() - started
    print()
    print("=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    print(f"  Stocks processed: {len(target_ids)}")
    print(f"  Rows inserted:    {total_inserted}")
    print(f"  Failed:           {total_failed}")
    print(f"  No new data:      {total_skipped}")
    print(f"  Time:             {elapsed:.0f}s ({elapsed/60:.1f}m)")
    print(f"  Avg per stock:    {(elapsed / max(len(target_ids), 1)):.1f}s")
    print()

    if total_failed > 0:
        print("  ⚠  Some stocks failed. Re-run without --force to retry just those.")
        sys.exit(1)
    else:
        print("  ✓ stock_prices refill complete.")
        print("  ✓ Kronos pre-filter will now find >200 rows and stop skipping stocks.")


if __name__ == "__main__":
    main()
