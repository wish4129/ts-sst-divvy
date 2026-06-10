"""Sync script: reads Supabase DB → generates stocks.ts and portfolios.json.

Usage: python3 scripts/sync_from_db.py

DB is the single source of truth. stocks.ts and portfolios.json are generated artifacts.
"""
import json, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from db import get_db
from persona_db import TICKER_TO_SHORT, SHORT_TO_TICKER

MYT = timezone(timedelta(hours=8))
NOW = datetime.now(MYT).strftime("%Y-%m-%d")

# ── Fetch from DB ──

db = get_db()
cur = db.cursor()

cur.execute("""
    SELECT id, name, industry, status, score_composite, score_subs,
           last_price, price_change, dividend_yield, market_cap,
           sparkline, notes, kronos_warning, revisit_at, 
           COALESCE(financials::text, '[]') as financials_json,
           COALESCE(dividends::text, '[]') as dividends_json
    FROM stocks
    WHERE status != 'removed'
    ORDER BY score_composite DESC
""")

stocks = []
_ticker_short_map = {}  # ticker → short_code for TS exports
for row in cur.fetchall():
    (ticker, name, industry, status, composite, score_subs_raw,
     price, price_change, dy, mcap, sparkline_raw, notes,
     kronos_warning, revisit_at, fin_json, div_json) = row
    
    short_code = TICKER_TO_SHORT.get(ticker, ticker.replace('.KL', ''))
    _ticker_short_map[ticker] = short_code
    
    scores = json.loads(score_subs_raw) if isinstance(score_subs_raw, str) else (score_subs_raw or {})
    financials = json.loads(fin_json) if isinstance(fin_json, str) else (fin_json or [])
    dividends = json.loads(div_json) if isinstance(div_json, str) else (div_json or [])
    sparkline = json.loads(sparkline_raw) if isinstance(sparkline_raw, str) else (sparkline_raw or [])
    
    stocks.append({
        'code': short_code,
        'name': name,
        'industry': industry or '',
        'marketCap': float(mcap or 0),
        'lastPrice': float(price or 0),
        'priceChange': float(price_change or 0),
        'dividendYield': float(dy or 0),
        'score_composite': int(composite or 0),
        'score_dividend': scores.get('dividend', 0),
        'score_growth': scores.get('growth', 0),
        'score_quality': scores.get('quality', 0),
        'score_risk': scores.get('risk', 0),
        'financials': financials,
        'dividends': dividends,
        'status': status or 'revisit',
        'notes': notes or '',
        'sparkline': sparkline,
        'revisit_at': revisit_at,
    })

cur.close()
db.close()

print(f"Fetched {len(stocks)} stocks from DB")

# ── Generate stocks.ts ──

lines = []
lines.append("""export interface StockScore {
  composite: number
  dividend: number
  growth: number
  quality: number
  risk: number
}

export interface StockFinancials {
  quarter: string
  revenue: number
  netIncome: number
  freeCashFlow: number
  peRatio: number
  pbRatio?: number
  roe: number
  debtToEquity: number
  revenueGrowthYoY: number
}

export interface DividendRecord {
  exDate: string
  amount: number
  yield: number
}

export interface Stock {
  code: string
  name: string
  industry: string
  marketCap: number
  lastPrice: number
  priceChange: number
  dividendYield: number
  score: StockScore
  financials: StockFinancials[]
  dividends: DividendRecord[]
  status: 'active' | 'revisit' | 'removed'
  addedAt: string
  revisitAt: string | null
  notes: string
  sparkline: number[]
}

export const stocks: Stock[] = [""")

for i, s in enumerate(stocks):
    fin_str = json.dumps(s['financials'])
    div_str = json.dumps(s['dividends'])
    spark_str = json.dumps(s['sparkline'])
    revisit = 'null' if not s['revisit_at'] else f"'{s['revisit_at']}'"
    comma = ',' if i < len(stocks) - 1 else ''
    
    esc_name = s['name'].replace("'", "\\'")
    esc_notes = s['notes'].replace("'", "\\'")
    
    lines.append(f"  {{")
    lines.append(f"    code: '{s['code']}',")
    lines.append(f"    name: '{esc_name}',")
    lines.append(f"    industry: '{s['industry']}',")
    lines.append(f"    marketCap: {s['marketCap']},")
    lines.append(f"    lastPrice: {s['lastPrice']},")
    lines.append(f"    priceChange: {s['priceChange']},")
    lines.append(f"    dividendYield: {s['dividendYield']},")
    lines.append(f"    score: {{ composite: {s['score_composite']}, dividend: {s['score_dividend']}, growth: {s['score_growth']}, quality: {s['score_quality']}, risk: {s['score_risk']} }},")
    lines.append(f"    financials: {fin_str},")
    lines.append(f"    dividends: {div_str},")
    lines.append(f"    status: '{s['status']}',")
    lines.append(f"    addedAt: '{NOW}',")
    lines.append(f"    revisitAt: {revisit},")
    lines.append(f"    notes: '{esc_notes}',")
    lines.append(f"    sparkline: {spark_str},")
    lines.append(f"  }}{comma}")

# Build SHORT_TO_TICKER TS lines
lines.append("""
]

// Auto-generated ticker maps from DB sync
export const SHORT_TO_TICKER: Record<string, string> = {
""")
ticker_items = sorted(SHORT_TO_TICKER.items())
for i, (short_code, t) in enumerate(ticker_items):
    comma = ',' if i < len(ticker_items) - 1 else ''
    lines.append(f"  '{short_code}': '{t}'{comma}")
lines.append("""}

export const TICKER_TO_SHORT: Record<string, string> = {}
for (const [short, ticker] of Object.entries(SHORT_TO_TICKER)) {
  TICKER_TO_SHORT[ticker] = short
}

export const INDUSTRY_COLORS: Record<string, string> = {
  Banking: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  Utilities: 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200',
  REIT: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
  Plantation: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  Telco: 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900 dark:text-cyan-200',
  Tech: 'bg-violet-100 text-violet-800 dark:bg-violet-900 dark:text-violet-200',
  Consumer: 'bg-pink-100 text-pink-800 dark:bg-pink-900 dark:text-pink-200',
  'Oil & Gas': 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  Healthcare: 'bg-teal-100 text-teal-800 dark:bg-teal-900 dark:text-teal-200',
  Construction: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
  'Consumer Products & Services': 'bg-pink-100 text-pink-800 dark:bg-pink-900 dark:text-pink-200',
  Automotive: 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900 dark:text-cyan-200',
  Energy: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  Packaging: 'bg-teal-100 text-teal-800 dark:bg-teal-900 dark:text-teal-200',
  Furniture: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  Industrial: 'bg-slate-100 text-slate-800 dark:bg-slate-900 dark:text-slate-200',
  Investment: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200',
  Semiconductor: 'bg-violet-100 text-violet-800 dark:bg-violet-900 dark:text-violet-200',
  Conglomerate: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200',
  Property: 'bg-lime-100 text-lime-800 dark:bg-lime-900 dark:text-lime-200',
}
""")

ts_output = '\n'.join(lines) + '\n'
ts_path = ROOT / 'web' / 'src' / 'data' / 'stocks.ts'
ts_path.write_text(ts_output)
print(f"  Wrote {ts_path} ({len(ts_output)} bytes)")

print(f"\nSync complete — {len(stocks)} stocks in DB → stocks.ts")
