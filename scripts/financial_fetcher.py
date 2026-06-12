"""Quarterly financial data fetcher — yfinance (free) → Supabase DB.

Extracts multi-quarter financials and writes directly to stocks.financials JSONB.
Usage: python3 scripts/financial_fetcher.py [stock_codes...]
Cron: weekly Monday morning
"""
import json
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    import yfinance as yf
    import pandas as pd
    import psycopg2
    import psycopg2.extras
except ImportError:
    import os
    os.system(f"{sys.executable} -m pip install yfinance pandas psycopg2-binary --quiet")
    import yfinance as yf
    import pandas as pd
    import psycopg2
    import psycopg2.extras

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from db import get_db

def _get_all_stocks_dict():
    """Get {short_name: {code, name, industry, initial}} for all stocks from DB."""
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT id, name, industry, initial_price FROM stocks WHERE status NOT IN ('removed', 'data_missing')")
    result = {}
    for r in cur.fetchall():
        short = r[0].replace('.KL', '')
        result[short] = {
            'code': r[0],
            'name': r[1],
            'industry': r[2] or '',
            'initial': float(r[3] or 0),
        }
    cur.close()
    db.close()
    return result

MALAYSIA_TZ = timezone(timedelta(hours=8))


def safe_float(val, default=None):
    try:
        v = float(val)
        return v if not (pd.isna(v) if isinstance(v, float) else False) else default
    except (ValueError, TypeError):
        return default


def extract_quarterly(ticker_code):
    """Extract all available quarters as array for DB storage."""
    try:
        t = yf.Ticker(ticker_code)
        qi = t.quarterly_financials
        bs = t.quarterly_balance_sheet
        cf = t.quarterly_cashflow
    except Exception as e:
        return None, {"error": str(e), "code": ticker_code}

    if qi is None or qi.empty:
        return None, {"error": "No quarterly data", "code": ticker_code}

    quarters = []
    for col_idx in range(min(len(qi.columns), 8)):  # up to 8 quarters
        col = qi.columns[col_idx]
        q_date = col.strftime("%Y-%m-%d") if hasattr(col, 'strftime') else str(col)

        revenue = safe_float(
            qi.loc["Total Revenue", col] if "Total Revenue" in qi.index else 0, 0
        )
        net_income = safe_float(
            qi.loc["Net Income", col] if "Net Income" in qi.index else 0, 0
        )
        free_cash_flow = safe_float(
            cf.loc["Free Cash Flow", cf.columns[min(col_idx, len(cf.columns)-1)]]
            if cf is not None and "Free Cash Flow" in cf.index
            else 0, 0
        )

        total_equity = safe_float(
            bs.loc["Stockholders Equity", bs.columns[min(col_idx, len(bs.columns)-1)]]
            if bs is not None and "Stockholders Equity" in bs.index
            else 0, 0
        )
        total_debt = safe_float(
            bs.loc["Total Debt", bs.columns[min(col_idx, len(bs.columns)-1)]]
            if bs is not None and "Total Debt" in bs.index
            else 0, 0
        )

        roe = (net_income / total_equity * 100) if total_equity and total_equity > 0 else 0

        # Revenue growth YoY (compare to same quarter last year)
        rev_growth = 0
        if col_idx + 4 < len(qi.columns):
            rev_4q_ago = safe_float(
                qi.loc["Total Revenue", qi.columns[col_idx + 4]]
                if "Total Revenue" in qi.index else 0, 0
            )
            if rev_4q_ago and rev_4q_ago > 0 and revenue:
                rev_growth = round((revenue - rev_4q_ago) / rev_4q_ago * 100, 1)

        quarters.append({
            "quarter": q_date,
            "revenue": round(revenue, 0),
            "netIncome": round(net_income, 0),
            "freeCashFlow": round(free_cash_flow, 0),
            "peRatio": 0,  # filled below from ticker info
            "roe": round(roe, 1),
            "debtToEquity": round(total_debt / total_equity, 1) if total_equity and total_equity > 0 else 0,
            "revenueGrowthYoY": rev_growth,
        })

    # Get valuation from ticker.info
    try:
        ti = t.info
        pe = safe_float(ti.get("trailingPE"), 0)
        dy = safe_float(ti.get("dividendYield"), 0)
        # yfinance returns dividendYield as percentage already
        # (e.g., 0.84 = 0.84%, 16.57 = 16.57%), NOT decimal fraction.
        # No multiplication needed.
        mcap = safe_float(ti.get("marketCap"), 0)
        price = safe_float(ti.get("currentPrice") or ti.get("regularMarketPrice"), 0)
        roe_val = safe_float(ti.get("returnOnEquity"), 0)
        if roe_val and roe_val < 1:
            roe_val = roe_val * 100
        de_val = safe_float(ti.get("debtToEquity"), 0)
        # yfinance returns D/E as percentage for MY stocks (e.g., 92.7 = 92.7%).
        # Convert to ratio. If missing (banks, etc.), fall back to quarterly BS.
        if de_val and de_val > 0:
            de_val = round(de_val / 100, 3)
        else:
            # Fallback: compute from latest quarter's balance sheet
            de_val = quarters[0]["debtToEquity"] if quarters and quarters[0].get("debtToEquity") else 0

        # Fill PE into latest quarter
        if quarters and pe:
            quarters[0]["peRatio"] = round(pe, 1)
    except Exception:
        pe = dy = mcap = price = roe_val = de_val = 0

    summary = {
        "pe": round(pe, 1) if pe else None,
        "roe": round(roe_val, 1) if roe_val else None,
        "dy": round(dy, 2) if dy else None,
        "mcap": round(mcap / 1_000_000, 2) if mcap else None,
        "de": round(de_val, 3) if de_val else None,
        "price": round(price, 2) if price else None,
    }

    return quarters, summary


def main():
    stocks = _get_all_stocks_dict()
    target_codes = sys.argv[1:] if len(sys.argv) > 1 else [
        info["code"] for info in stocks.values()
    ]

    print(f"[{datetime.now(MALAYSIA_TZ).isoformat()}] Fetching financials for {len(target_codes)} stocks...")

    conn = get_db()
    cur = conn.cursor()
    success = 0
    errors = 0

    for code in target_codes:
        print(f"  {code}...", end=" ", flush=True)
        try:
            quarters, summary = extract_quarterly(code)

            if quarters is None:
                print(f"⚠ {summary.get('error', 'unknown')}")
                errors += 1
                continue

            cur.execute(
                """UPDATE stocks SET
                    financials = %s,
                    pe_ratio = %s,
                    roe = %s,
                    dividend_yield = %s,
                    market_cap = %s,
                    debt_to_equity = %s,
                    last_price = COALESCE(%s, last_price),
                    status = CASE WHEN status = 'data_missing' THEN 'revisit' ELSE status END,
                    updated_at = now()
                WHERE id = %s""",
                (
                    json.dumps(quarters),
                    summary["pe"],
                    summary["roe"],
                    summary["dy"],
                    summary["mcap"],
                    summary["de"],
                    summary["price"],
                    code + ".KL" if not code.endswith(".KL") else code,
                ),
            )
            conn.commit()
            # If this was a data_missing re-fetch, mark it processed
            cur.execute("UPDATE pending_analyses SET processed=TRUE, processed_at=NOW() WHERE stock_code=%s AND source='data_missing_queue'", (code,))
            conn.commit()
            print(f"✓ {len(quarters)}q PE={summary['pe']} ROE={summary['roe']}% DY={summary['dy']}%")
            success += 1
        except Exception as e:
            conn.rollback()
            print(f"✗ {e}")
            errors += 1
        time.sleep(0.3)  # rate limit

    cur.close()
    conn.close()
    print(f"\n✓ {success} fetched, {errors} errors")


if __name__ == "__main__":
    main()
