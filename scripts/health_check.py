#!/usr/bin/env python3
"""Divvy Health Check Dashboard — queries Supabase Postgres directly."""
import os, sys
sys.path.insert(0, os.path.expanduser("~/xiongit/divvy/scripts"))
from db import get_db, dict_cursor

conn = get_db()
cur = dict_cursor(conn)

def section(s):
    print(f"\n## {s}\n")

def table(header, rows):
    sep = " | ".join(["---"] * len(header))
    print(" | ".join(header))
    print(sep)
    for r in rows:
        print(" | ".join(str(c) for c in r))
    print()

# ============================================================
# 1. SCORE DISTRIBUTION (use score_composite from stock_analyses)
# ============================================================
section("1. Score Distribution (score_composite)")

cur.execute("""
SELECT
  CASE
    WHEN score_composite IS NULL THEN 'No score'
    WHEN score_composite >= 80 THEN '80-100'
    WHEN score_composite >= 60 THEN '60-80'
    WHEN score_composite >= 40 THEN '40-60'
    WHEN score_composite >= 20 THEN '20-40'
    ELSE '0-20'
  END AS bracket,
  COUNT(*) AS count,
  ROUND(100.0 * COUNT(*) / NULLIF((SELECT COUNT(*) FROM stock_analyses WHERE score_composite IS NOT NULL), 0), 1) AS pct
FROM stock_analyses
GROUP BY bracket
ORDER BY bracket;
""")
rows = cur.fetchall()
table(["Bracket", "Count", "% of Scored"],
      [(r['bracket'], r['count'], r['pct']) for r in rows])

cur.execute("SELECT COUNT(*) AS c FROM stock_analyses WHERE score_composite IS NOT NULL")
scored = cur.fetchone()['c']
cur.execute("SELECT COUNT(*) AS c FROM stocks")
total = cur.fetchone()['c']
print(f"**Scored: {scored} / {total} stocks**\n")

# ============================================================
# 2. KRONOS FRESHNESS
# ============================================================
section("2. Kronos Freshness (>7 days old)")

cur.execute("""
SELECT s.id AS ticker, s.name, kf.generated_at,
  CAST(EXTRACT(EPOCH FROM NOW() - kf.generated_at) / 86400 AS INTEGER) AS age_days
FROM kronos_forecasts kf
JOIN stocks s ON s.id = kf.stock_id
WHERE kf.generated_at < NOW() - INTERVAL '7 days'
ORDER BY kf.generated_at ASC
LIMIT 20;
""")
rows = cur.fetchall()
if rows:
    table(["Ticker", "Name", "Generated", "Age(d)"],
          [(r['ticker'], r['name'], str(r['generated_at'])[:19], r['age_days']) for r in rows])
    print(f"**{len(rows)} stale forecasts found**")
else:
    print("✅ All forecasts are fresh (<7 days)")
cur.execute("SELECT COUNT(*) AS c FROM kronos_forecasts")
print(f"**Total forecasts: {cur.fetchone()['c']}**\n")

# ============================================================
# 3. STALE FINANCIALS
# ============================================================
section("3. Stale Financials (>30 days)")

cur.execute("""
SELECT s.id AS ticker, s.name, st.updated_at AS last_updated,
  CAST(EXTRACT(EPOCH FROM NOW() - st.updated_at) / 86400 AS INTEGER) AS age_days
FROM stocks st
JOIN stocks s ON s.id = st.id
WHERE st.financials IS NOT NULL AND st.updated_at < NOW() - INTERVAL '30 days'
ORDER BY st.updated_at ASC
LIMIT 20;
""")
rows = cur.fetchall()
if rows:
    table(["Ticker", "Name", "Last Updated", "Age(d)"],
          [(r['ticker'], r['name'], str(r['last_updated'])[:19], r['age_days']) for r in rows])
    print(f"**{len(rows)} stocks with stale financials**")
else:
    print("✅ All financials are fresh (<30 days)")
# Count all with financials
cur.execute("SELECT COUNT(*) AS c FROM stocks WHERE financials IS NOT NULL")
print(f"**Stocks with financials: {cur.fetchone()['c']}**\n")

# ============================================================
# 4. MISSING ANALYSES
# ============================================================
section("4. Missing Stock Analyses")

cur.execute("""
SELECT s.id AS ticker, s.name, s.status
FROM stocks s LEFT JOIN stock_analyses sa ON sa.stock_id = s.id
WHERE sa.id IS NULL
ORDER BY s.id
LIMIT 20;
""")
rows = cur.fetchall()
if rows:
    for r in rows:
        print(f"❌ {r['ticker']:10s} {r['name']:20s} [{r['status']}]")
    print(f"**{len(rows)} shown out of ", end="")
    cur.execute("SELECT COUNT(*) AS c FROM stocks s LEFT JOIN stock_analyses sa ON sa.stock_id = s.id WHERE sa.id IS NULL")
    print(f"{cur.fetchone()['c']} total missing**")
else:
    print("✅ All stocks have analyses")
print()

# ============================================================
# 5. STATUS DRIFT
# ============================================================
section("5. Status Drift")

# Active stocks with low score
cur.execute("""
SELECT s.id AS ticker, s.name, sa.score_composite, s.status
FROM stocks s JOIN stock_analyses sa ON sa.stock_id = s.id
WHERE s.status = 'active' AND sa.score_composite < 70
ORDER BY sa.score_composite ASC
LIMIT 20;
""")
active_low = cur.fetchall()
if active_low:
    print(f"**Active scoring <70:** {len(active_low)}")
    for r in active_low:
        print(f"  ⚠ {r['ticker']:10s} {r['name']:20s} score={r['score_composite']}")
else:
    print("✅ No active stocks with score_composite <70")
print()

# Revisit stocks with high score
cur.execute("""
SELECT s.id AS ticker, s.name, sa.score_composite, s.status
FROM stocks s JOIN stock_analyses sa ON sa.stock_id = s.id
WHERE s.status = 'revisit' AND sa.score_composite >= 70
ORDER BY sa.score_composite DESC
LIMIT 20;
""")
revisit_high = cur.fetchall()
if revisit_high:
    print(f"**Revisit scoring >=70:** {len(revisit_high)}")
    for r in revisit_high:
        print(f"  ⚠ {r['ticker']:10s} {r['name']:20s} score={r['score_composite']}")
else:
    print("✅ No revisit stocks with score_composite >=70")
print()

# ============================================================
# 6. ADDITIONAL: Score from stocks table
# ============================================================
section("6. Stocks.score_composite Distribution")

cur.execute("""
SELECT
  CASE
    WHEN score_composite IS NULL THEN 'No score'
    WHEN score_composite >= 80 THEN '80-100'
    WHEN score_composite >= 60 THEN '60-80'
    WHEN score_composite >= 40 THEN '40-60'
    WHEN score_composite >= 20 THEN '20-40'
    ELSE '0-20'
  END AS bracket,
  COUNT(*) AS count,
  ROUND(100.0 * COUNT(*) / NULLIF((SELECT COUNT(*) FROM stocks WHERE score_composite IS NOT NULL), 0), 1) AS pct
FROM stocks
GROUP BY bracket
ORDER BY bracket;
""")
rows = cur.fetchall()
table(["Bracket", "Count", "% of Scored"],
      [(r['bracket'], r['count'], r['pct']) for r in rows])
cur.execute("SELECT COUNT(*) AS c FROM stocks WHERE score_composite IS NOT NULL")
print(f"**Scored (stocks table): {cur.fetchone()['c']}**\n")

# ============================================================
# SUMMARY
# ============================================================
section("Summary")

cur.execute("SELECT COUNT(*) AS c FROM stocks s LEFT JOIN stock_analyses sa ON sa.stock_id = s.id WHERE sa.id IS NULL")
missing_count = cur.fetchone()['c']

print("| Metric | Value |")
print("|--------|-------|")
print(f"| Total stocks | {total} |")
print(f"| Scored (analyses) | {scored} |")
print(f"| Missing analyses | {missing_count} |")
print(f"| Active <70 / Revisit >=70 | {len(active_low)} / {len(revisit_high)} |")

from datetime import datetime, timezone
print(f"\n**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")

conn.close()
