#!/usr/bin/env python3
"""Divvy DB health audit — one-shot script covering all key metrics.

Usage:
    cd ~/xiongit/divvy && .venv/bin/python3 scripts/db_health_audit.py
    cd ~/xiongit/divvy && .venv/bin/python3 scripts/db_health_audit.py --energy  # + O&G scan

Covers: AI report coverage, stock distribution, Kronos coverage/gaps,
        bursa universe analysis ratio, industry tag coverage, ACE Market stats,
        timestamp freshness, unscored stocks.
"""

import sys
import os

# Run from project root: cd ~/xiongit/divvy && .venv/bin/python3 scripts/db_health_audit.py
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PROJECT_SCRIPTS = os.path.join(_PROJECT_ROOT, 'scripts')
if os.path.exists(os.path.join(_PROJECT_SCRIPTS, 'db.py')):
    sys.path.insert(0, _PROJECT_SCRIPTS)
else:
    sys.path.insert(0, 'scripts')

from db import get_db


def baseline_audit(cur):
    """Core health metrics."""
    # AI report coverage (distinct stocks)
    cur.execute(
        "SELECT COUNT(DISTINCT stock_id) FROM stock_analyses "
        "WHERE score_composite IS NOT NULL AND ai_report IS NOT NULL"
    )
    ai_covered = cur.fetchone()[0]
    cur.execute(
        "SELECT COUNT(DISTINCT stock_id) FROM stock_analyses "
        "WHERE score_composite IS NOT NULL AND ai_report IS NULL"
    )
    ai_missing = cur.fetchone()[0]
    total = ai_covered + ai_missing
    pct = ai_covered / total * 100 if total else 0
    print(f"AI report coverage: {ai_covered} scored+AI, {ai_missing} scored-no-AI "
          f"({ai_covered}/{total} = {pct:.1f}%)")

    # Stock distribution
    cur.execute("SELECT status, COUNT(*) FROM stocks GROUP BY status ORDER BY status")
    print(f"Stock distribution: {cur.fetchall()}")

    # Kronos coverage + gap detection
    cur.execute("SELECT COUNT(DISTINCT stock_id) FROM kronos_forecasts")
    kronos_cov = cur.fetchone()[0]
    cur.execute(
        "SELECT s.id, s.name FROM stocks s "
        "WHERE s.id NOT IN (SELECT DISTINCT stock_id FROM kronos_forecasts) LIMIT 5"
    )
    kronos_gaps = cur.fetchall()
    print(f"Kronos coverage: {kronos_cov} distinct stocks, "
          f"gaps: {len(kronos_gaps)} {[r[0] for r in kronos_gaps]}")

    # Bursa universe
    cur.execute("SELECT COUNT(*) FROM bursa_universe WHERE has_analysis = true")
    bu_analyzed = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM bursa_universe")
    bu_total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM bursa_universe WHERE industry IS NOT NULL")
    bu_industry = cur.fetchone()[0]
    print(f"Bursa universe: {bu_analyzed}/{bu_total} analyzed, "
          f"{bu_industry}/{bu_total} with industry tags")

    # ACE Market (0xxx codes, 7-char like '0192.KL')
    cur.execute(
        "SELECT COUNT(*) FROM bursa_universe "
        "WHERE stock_code LIKE '0%' AND LENGTH(stock_code) = 7"
    )
    ace_total = cur.fetchone()[0]
    cur.execute(
        "SELECT COUNT(*) FROM bursa_universe "
        "WHERE has_analysis = true AND stock_code LIKE '0%' AND LENGTH(stock_code) = 7"
    )
    ace_analyzed = cur.fetchone()[0]
    print(f"ACE Market: {ace_analyzed}/{ace_total} analyzed")

    # Timestamps (freshness)
    cur.execute("SELECT MAX(generated_at) FROM kronos_forecasts")
    kronos_max = cur.fetchone()[0]
    cur.execute("SELECT MAX(generated_at) FROM stock_analyses WHERE ai_report IS NOT NULL")
    ai_max = cur.fetchone()[0]
    print(f"Latest Kronos: {kronos_max}, Latest AI report: {ai_max}")

    # Unscored stocks
    cur.execute(
        "SELECT s.id, s.name FROM stocks s "
        "LEFT JOIN stock_analyses sa ON s.id = sa.stock_id "
        "WHERE sa.stock_id IS NULL OR sa.id IS NULL LIMIT 5"
    )
    unscored = cur.fetchall()
    print(f"Unscored stocks: {len(unscored)} {[r[0] for r in unscored]}")

    # Total scored stocks
    cur.execute("SELECT COUNT(DISTINCT stock_id) FROM stock_analyses WHERE score_composite IS NOT NULL")
    total_scored = cur.fetchone()[0]
    print(f"Total scored stocks (stock_analyses): {total_scored}")

    # Industry tag breakdown
    cur.execute(
        "SELECT industry, COUNT(*) FROM bursa_universe "
        "WHERE industry IS NOT NULL GROUP BY industry ORDER BY COUNT(*) DESC"
    )
    print(f"Industry tags: {cur.fetchall()}")


def energy_scan(cur):
    """Energy/O&G/solar/renewable companies in bursa_universe."""
    cur.execute(
        "SELECT stock_code, name FROM bursa_universe "
        "WHERE (LOWER(name) LIKE '%oil%' OR LOWER(name) LIKE '%gas%' "
        "   OR LOWER(name) LIKE '%energy%' OR LOWER(name) LIKE '%petrol%' "
        "   OR LOWER(name) LIKE '%offshore%' OR LOWER(name) LIKE '%marine%' "
        "   OR LOWER(name) LIKE '%solar%' OR LOWER(name) LIKE '%renew%') "
        "ORDER BY name LIMIT 40"
    )
    companies = cur.fetchall()
    print(f"\nEnergy/O&G companies ({len(companies)}):")
    for r in companies:
        cur.execute(
            "SELECT s.status, sa.score_composite FROM stocks s "
            "LEFT JOIN stock_analyses sa ON s.id = sa.stock_id "
            "AND sa.score_composite IS NOT NULL "
            "WHERE s.id = %s ORDER BY sa.generated_at DESC LIMIT 1",
            (r[0],),
        )
        row = cur.fetchone()
        status = row[0] if row else "NOT_ANALYZED"
        score = float(row[1]) if row and row[1] else 0
        print(f"  {r[0]} | {r[1][:55]:55s} | {status:15s} | {score}")


if __name__ == "__main__":
    run_energy = "--energy" in sys.argv

    db = get_db()
    cur = db.cursor()
    try:
        baseline_audit(cur)
        if run_energy:
            energy_scan(cur)
    finally:
        db.close()
