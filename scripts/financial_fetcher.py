"""Quarterly financial data fetcher — yfinance (free).

Extracts key metrics for industry scoring from quarterly financials.
Output: data/stock_financials.json

Usage: python3 scripts/financial_fetcher.py
Cron: 0 8 * * 1  (weekly Monday morning)
"""
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    import yfinance as yf
    import pandas as pd
except ImportError:
    import os; os.system(f"{sys.executable} -m pip install yfinance --quiet")
    import yfinance as yf
    import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from persona_db import get_all_stocks_dict
OUTPUT_PATH = ROOT / "data" / "stock_financials.json"

MALAYSIA_TZ = timezone(timedelta(hours=8))

# ── Load stocks from DB ──
stocks = get_all_stocks_dict()  # {short_name: {code, name, industry, initial}}
tickers = [info["code"] for info in stocks.values()]

print(f"[{datetime.now(MALAYSIA_TZ).isoformat()}] Fetching financials for {len(stocks)} stocks...")


def safe_float(val, default=None):
    """Safely convert to float, handling NaN."""
    try:
        v = float(val)
        return v if not pd.isna(v) else default
    except (ValueError, TypeError):
        return default


def extract_financials(ticker, info):
    """Extract key financial metrics from yfinance quarterly data."""
    try:
        t = yf.Ticker(info["code"])
        qi = t.quarterly_financials  # Most recent 4 quarters
        bs = t.quarterly_balance_sheet
        cf = t.quarterly_cashflow
    except Exception as e:
        return {"error": str(e), "code": info["code"]}

    if qi is None or qi.empty:
        return {"error": "No quarterly data", "code": info["code"]}

    # Latest quarter
    latest = qi.columns[0]  # Most recent quarter date
    q_latest = latest.strftime("%Y-%m-%d") if hasattr(latest, 'strftime') else str(latest)

    # ── Income Statement ──
    revenue = safe_float(qi.loc["Total Revenue", latest] if "Total Revenue" in qi.index else 0, 0)
    net_income = safe_float(qi.loc["Net Income", latest] if "Net Income" in qi.index else 0, 0)
    gross_profit = safe_float(qi.loc["Gross Profit", latest] if "Gross Profit" in qi.index else 0, 0)
    operating_income = safe_float(qi.loc["Operating Income", latest] if "Operating Income" in qi.index else 0, 0)

    # Gross margin
    gross_margin = (gross_profit / revenue * 100) if revenue and revenue > 0 else None

    # Revenue growth YoY
    if len(qi.columns) >= 5:
        revenue_4q_ago = safe_float(qi.loc["Total Revenue", qi.columns[4]] if "Total Revenue" in qi.index else 0, 0)
        revenue_growth_yoy = ((revenue - revenue_4q_ago) / revenue_4q_ago * 100) if revenue_4q_ago and revenue_4q_ago > 0 else None
    else:
        revenue_growth_yoy = None

    # ── Balance Sheet ──
    total_assets = safe_float(bs.loc["Total Assets", bs.columns[0]] if bs is not None and "Total Assets" in bs.index else 0, 0)
    total_debt = safe_float(bs.loc["Total Debt", bs.columns[0]] if bs is not None and "Total Debt" in bs.index else 0, 0)
    total_equity = safe_float(bs.loc["Stockholders Equity", bs.columns[0]] if bs is not None and "Stockholders Equity" in bs.index else 0, 0)
    cash = safe_float(bs.loc["Cash And Cash Equivalents", bs.columns[0]] if bs is not None and "Cash And Cash Equivalents" in bs.index else 0, 0)

    de_ratio = (total_debt / total_equity) if total_equity and total_equity > 0 else None
    cash_per_share = cash / info.get("shares_outstanding", 1) if cash else None

    # ── Cash Flow ──
    free_cash_flow = safe_float(cf.loc["Free Cash Flow", cf.columns[0]] if cf is not None and "Free Cash Flow" in cf.index else 0, 0)

    # ── ROE ──
    roe = (net_income / total_equity * 100) if total_equity and total_equity > 0 else None

    # ── Valuation (from ticker.info) ──
    try:
        ti = t.info
        pe_ratio = safe_float(ti.get("trailingPE"), None)
        pb_ratio = safe_float(ti.get("priceToBook"), None)
        dividend_yield = safe_float(ti.get("dividendYield"), None)
        # yfinance gives dividend yield as decimal (0.05 = 5%), convert to %
        if dividend_yield and dividend_yield < 1:
            dividend_yield = dividend_yield * 100
        market_cap = safe_float(ti.get("marketCap"), None)
        current_price = safe_float(ti.get("currentPrice") or ti.get("regularMarketPrice"), None)
    except Exception:
        pe_ratio = pb_ratio = dividend_yield = market_cap = current_price = None

    return {
        "code": info["code"],
        "name": info["name"],
        "industry": info.get("industry", ""),
        "quarter": q_latest,
        "current_price": round(current_price, 4) if current_price else None,
        "market_cap_m": round(market_cap / 1_000_000, 2) if market_cap else None,
        # Income
        "revenue_m": round(revenue / 1_000_000, 2) if revenue else 0,
        "net_income_m": round(net_income / 1_000_000, 2) if net_income else 0,
        "gross_margin_pct": round(gross_margin, 2) if gross_margin else None,
        "revenue_growth_yoy_pct": round(revenue_growth_yoy, 2) if revenue_growth_yoy is not None else None,
        # Balance sheet
        "de_ratio": round(de_ratio, 4) if de_ratio is not None else None,
        "total_debt_m": round(total_debt / 1_000_000, 2) if total_debt else 0,
        "total_equity_m": round(total_equity / 1_000_000, 2) if total_equity else 0,
        "cash_per_share": round(cash_per_share, 4) if cash_per_share else None,
        # Cash flow
        "free_cash_flow_m": round(free_cash_flow / 1_000_000, 2) if free_cash_flow else 0,
        # Ratios
        "roe_pct": round(roe, 2) if roe else None,
        "pe_ratio": round(pe_ratio, 2) if pe_ratio else None,
        "pb_ratio": round(pb_ratio, 4) if pb_ratio else None,
        "dividend_yield_pct": round(dividend_yield, 2) if dividend_yield else None,
    }


# ── Fetch all ──
results = {}
for name, info in stocks.items():
    code = info["code"]
    print(f"  {name:10s} ({code})...", end=" ", flush=True)
    try:
        data = extract_financials(info["code"], info)
        if "error" in data:
            print(f"⚠ {data['error']}")
        else:
            print(f"✓ Q={data['quarter']} PE={data['pe_ratio']} DY={data['dividend_yield_pct']}% ROE={data['roe_pct']}%")
        results[name] = data
    except Exception as e:
        print(f"✗ {e}")
        results[name] = {"code": code, "error": str(e)}

# ── Summary ──
success = sum(1 for r in results.values() if "error" not in r)
errors = sum(1 for r in results.values() if "error" in r)
print(f"\n✓ {success} fetched, {errors} errors")

# ── Save ──
output = {
    "date": datetime.now(MALAYSIA_TZ).strftime("%Y-%m-%d"),
    "stocks": results,
}
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH.write_text(json.dumps(output, indent=2))
print(f"✓ Saved to {OUTPUT_PATH}")
