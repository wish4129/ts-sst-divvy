"""Backfill all stocks from stocks.ts into the expanded DB."""
import json, re, sys
sys.path.insert(0, 'scripts')
from db import get_db

ts_path = 'web/src/data/stocks.ts'
content = open(ts_path).read()

# Extract each stock block with all fields
stock_pattern = re.compile(
    r"code:\s*'([^']+)'.*?"
    r"name:\s*'([^']+)'.*?"
    r"industry:\s*'([^']+)'.*?"
    r"marketCap:\s*([\d.]+).*?"
    r"lastPrice:\s*([\d.]+).*?"
    r"priceChange:\s*([\d.-]+).*?"
    r"dividendYield:\s*([\d.]+).*?"
    r"score:\s*\{\s*composite:\s*(\d+),\s*dividend:\s*(\d+),\s*growth:\s*(\d+),\s*quality:\s*(\d+),\s*risk:\s*(\d+)\s*\}.*?"
    r"status:\s*'([^']+)'.*?"
    r"addedAt:\s*'([^']+)'.*?"
    r"revisitAt:\s*(null|'[^']*').*?"
    r"notes:\s*'([^']*)'.*?"
    r"sparkline:\s*\[([^\]]+)\]",
    re.DOTALL
)

SHORT_TO_TICKER = {
    'MAYBANK': '1155.KL', 'AXREIT': '5106.KL', 'YTLPOWR': '6742.KL',
    'INSAS': '3379.KL', 'LIIHEN': '7089.KL', 'SCIENTEX': '4731.KL',
    'GENETEC': '0104.KL', 'KLK': '2445.KL', 'INARI': '0166.KL',
    'SIME': '4197.KL', 'MAGNI': '7087.KL', 'MBMR': '5983.KL',
    'AME': '5293.KL', 'DELEUM': '5132.KL', 'WASCO': '5142.KL',
    'KIPREIT': '5280.KL', 'INTA': 'INTA.KL',
    'RHB': '1066.KL', 'PADINI': '7052.KL',
    'GAMUDA': '5398.KL', 'MATRIX': '5236.KL',
    'PBBANK': '1295.KL', 'TIME': '5031.KL', 'SCICOM': '0099.KL',
    'SEM': '5250.KL', 'HEINEKEN': '3255.KL',
}

db = get_db()
cur = db.cursor()
count = 0

for m in stock_pattern.finditer(content):
    code = m.group(1)
    ticker = SHORT_TO_TICKER.get(code, code + '.KL')
    name = m.group(2)
    industry = m.group(3)
    market_cap = float(m.group(4))
    last_price = float(m.group(5))
    price_change = float(m.group(6))
    dividend_yield = float(m.group(7))
    composite = int(m.group(8))
    div_score = int(m.group(9))
    growth_score = int(m.group(10))
    quality_score = int(m.group(11))
    risk_score = int(m.group(12))
    status = m.group(13)
    revisit_at_raw = m.group(15)
    revisit_at = None if revisit_at_raw == 'null' else revisit_at_raw.strip("'\"")
    notes = m.group(16)
    sparkline_raw = m.group(17)
    
    sparkline = [float(x.strip()) for x in sparkline_raw.split(',') if x.strip()]
    
    score_subs = {
        'dividend': div_score,
        'growth': growth_score,
        'quality': quality_score,
        'risk': risk_score,
    }
    
    cur.execute('''
        INSERT INTO stocks (id, name, industry, initial_price, status, 
            score_composite, score_subs, last_price, price_change, 
            dividend_yield, market_cap, sparkline, notes, revisit_at, added_at, updated_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW(),NOW())
        ON CONFLICT (id) DO UPDATE SET
            name = EXCLUDED.name,
            industry = EXCLUDED.industry,
            score_composite = EXCLUDED.score_composite,
            score_subs = EXCLUDED.score_subs,
            last_price = EXCLUDED.last_price,
            price_change = EXCLUDED.price_change,
            dividend_yield = EXCLUDED.dividend_yield,
            market_cap = EXCLUDED.market_cap,
            sparkline = EXCLUDED.sparkline,
            notes = EXCLUDED.notes,
            status = EXCLUDED.status,
            revisit_at = EXCLUDED.revisit_at,
            updated_at = NOW()
    ''', (
        ticker, name, industry, last_price, status,
        composite, json.dumps(score_subs), last_price, price_change,
        dividend_yield, market_cap, json.dumps(sparkline), notes, revisit_at
    ))
    count += 1
    print(f'  ✓ {ticker} {name} ({status})')

db.commit()
cur.close()
db.close()
print(f'\n✓ Backfilled {count} stocks into DB')
