#!/usr/bin/env python3
"""Divvy DB Health Monitor — daily cron check.

Usage:
    cd ~/xiongit/divvy && python3 scripts/db_health_monitor.py

Reports all anomalies (non-silent) on failure, [SILENT] when healthy.

Checks:
  1. AI report coverage — every scored stock should have a report
  2. Kronos forecast coverage — tracks against stocks table
  3. Financials data freshness — oldest generated_at in stock_analyses
  4. Score=0 anomalies — stocks stuck at score=0 with non-null financials
  5. Stale running tasks in kanban board (>30 min)
"""

import os, sys, json, re, subprocess
from datetime import datetime, timezone, timedelta

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, 'scripts'))
from db import get_db

NOW = datetime.now(timezone.utc)
ISSUES = []


def check_ai_report_coverage(cur):
    """Every scored stock should have an AI report."""
    cur.execute("""
        SELECT COUNT(DISTINCT stock_id) FROM stock_analyses
        WHERE score_composite IS NOT NULL AND ai_report IS NOT NULL
    """)
    ai_covered = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(DISTINCT stock_id) FROM stock_analyses
        WHERE score_composite IS NOT NULL AND ai_report IS NULL
    """)
    ai_missing = cur.fetchone()[0]

    total = ai_covered + ai_missing
    pct = ai_covered / total * 100 if total else 0

    if ai_missing > 0:
        # List the first few
        cur.execute("""
            SELECT s.id, s.name FROM stocks s
            JOIN stock_analyses sa ON s.id = sa.stock_id
            WHERE sa.score_composite IS NOT NULL AND sa.ai_report IS NULL
            LIMIT 5
        """)
        gaps = [f"{r[0]} ({r[1]})" for r in cur.fetchall()]
        ISSUES.append(
            f"AI_REPORT_GAP: {ai_missing}/{total} scored stocks missing AI report "
            f"(coverage {pct:.1f}%). Examples: {', '.join(gaps)}"
        )
    else:
        print(f"AI report coverage: {ai_covered}/{total} ({pct:.1f}%) — OK")


def check_kronos_coverage(cur):
    """Kronos forecasts should cover most scored stocks."""
    cur.execute("SELECT COUNT(*) FROM stocks")
    total_stocks = cur.fetchone()[0]

    cur.execute("SELECT COUNT(DISTINCT stock_id) FROM kronos_forecasts")
    kronos_cov = cur.fetchone()[0]

    gap = total_stocks - kronos_cov
    if gap > 5:
        cur.execute("""
            SELECT s.id, s.name FROM stocks s
            WHERE s.id NOT IN (SELECT DISTINCT stock_id FROM kronos_forecasts)
            LIMIT 5
        """)
        gaps = [f"{r[0]} ({r[1]})" for r in cur.fetchall()]
        ISSUES.append(
            f"KRONOS_GAP: {gap} stocks missing Kronos forecasts "
            f"(covered {kronos_cov}/{total_stocks}). Examples: {', '.join(gaps)}"
        )
    else:
        print(f"Kronos coverage: {kronos_cov}/{total_stocks} ({gap} gaps) — OK")


def check_financials_freshness(cur):
    """Oldest financial data and stalest report."""
    cur.execute("SELECT MIN(generated_at) FROM stock_analyses WHERE ai_report IS NOT NULL")
    oldest_report = cur.fetchone()[0]

    cur.execute("SELECT MAX(generated_at) FROM stock_analyses WHERE ai_report IS NOT NULL")
    newest_report = cur.fetchone()[0]

    cur.execute("SELECT MAX(generated_at) FROM kronos_forecasts")
    newest_kronos = cur.fetchone()[0]

    stale_threshold = NOW - timedelta(hours=48)

    if oldest_report:
        oldest_age = (NOW - oldest_report.replace(tzinfo=timezone.utc)).total_seconds() / 3600
        print(f"Report age span: oldest={oldest_age:.0f}h, newest={(NOW - newest_report.replace(tzinfo=timezone.utc)).total_seconds()/3600:.0f}h")

    if newest_report:
        newest_age = (NOW - newest_report.replace(tzinfo=timezone.utc)).total_seconds() / 3600
        if newest_age > 48:
            ISSUES.append(
                f"STALE_REPORTS: newest AI report is {newest_age:.0f}h old "
                f"({newest_report.date()}) — older than 48h threshold"
            )

    if newest_kronos:
        kronos_age = (NOW - newest_kronos.replace(tzinfo=timezone.utc)).total_seconds() / 3600
        if kronos_age > 48:
            ISSUES.append(
                f"STALE_KRONOS: newest Kronos forecast is {kronos_age:.0f}h old "
                f"({newest_kronos.date()}) — older than 48h threshold"
            )

    print(f"Report freshness: newest={newest_report.date() if newest_report else 'N/A'}, "
          f"oldest={oldest_report.date() if oldest_report else 'N/A'}")
    print(f"Kronos freshness: newest={newest_kronos.date() if newest_kronos else 'N/A'}")


def check_score_zero_anomalies(cur):
    """Stocks stuck at score=0 with non-null financial data."""
    cur.execute("""
        SELECT COUNT(*) FROM stock_analyses
        WHERE score_composite IS NOT NULL AND score_composite = 0
    """)
    zero_scored = cur.fetchone()[0]

    # Look for stocks with score=0 but with financial data
    cur.execute("""
        SELECT s.id, s.name FROM stocks s
        JOIN stock_analyses sa ON s.id = sa.stock_id
        WHERE sa.score_composite = 0
          AND s.dividend_yield IS NOT NULL
        LIMIT 5
    """)
    stuck = cur.fetchall()
    if stuck:
        ISSUES.append(
            f"SCORE_ZERO_ANOMALY: {zero_scored} stocks at score=0. "
            f"{len(stuck)} have dividend_yield data but score=0: "
            f"{[f'{r[0]} ({r[1]})' for r in stuck]}"
        )
    else:
        print(f"Score=0 stocks: {zero_scored} — no stuck anomalies detected")


def check_stale_kanban_tasks():
    """Check kanban boards for tasks stuck in 'running' >30 min."""
    boards_dir = os.path.expanduser('~/.hermes/kanban/boards')
    if not os.path.isdir(boards_dir):
        return

    stale = []
    cutoff = NOW - timedelta(minutes=30)
    for board in os.listdir(boards_dir):
        db_path = os.path.join(boards_dir, board, 'kanban.db')
        if not os.path.isfile(db_path):
            continue
        try:
            rows = subprocess.run(
                ['sqlite3', '-separator', '|', db_path,
                 "SELECT id, title, started_at FROM tasks "
                 "WHERE status='running' AND started_at IS NOT NULL "
                 f"AND datetime(started_at, 'unixepoch') < '{cutoff.isoformat()}' "
                 "LIMIT 5"],
                capture_output=True, text=True, timeout=5
            ).stdout.strip()
            if rows:
                for line in rows.split('\n'):
                    parts = line.split('|')
                    if len(parts) >= 3:
                        stale.append(f"{board}/{parts[0]} ({parts[1]})")
        except Exception:
            pass

    if stale:
        ISSUES.append(f"STALE_TASKS: {len(stale)} tasks stuck in 'running' >30min: {', '.join(stale[:5])}")


def check_universe_analysis_ratio(cur):
    """Bursa universe analysis coverage."""
    cur.execute("SELECT COUNT(*) FROM bursa_universe WHERE has_analysis = true")
    analyzed = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM bursa_universe")
    total = cur.fetchone()[0]
    pct = analyzed / total * 100 if total else 0
    if pct < 10:
        ISSUES.append(
            f"LOW_ANALYSIS_RATIO: only {analyzed}/{total} bursa_universe analyzed ({pct:.1f}%)"
        )
    else:
        print(f"Bursa universe analysis: {analyzed}/{total} ({pct:.1f}%) — OK")


if __name__ == '__main__':
    try:
        db = get_db()
        cur = db.cursor()

        check_ai_report_coverage(cur)
        check_kronos_coverage(cur)
        check_financials_freshness(cur)
        check_score_zero_anomalies(cur)
        check_universe_analysis_ratio(cur)

        db.close()

        check_stale_kanban_tasks()

        if ISSUES:
            print("\n=== DB HEALTH ISSUES DETECTED ===")
            for issue in ISSUES:
                print(f"  [{issue.split(':')[0]}] {issue}")
            print(f"\n{len(ISSUES)} issue(s) found")
        else:
            print("\nAll checks passed — DB is healthy")
            print("[SILENT]")

    except Exception as e:
        print(f"DB_HEALTH_ERROR: Script failed — {e}")
        sys.exit(1)
