"""DB-first stock insert helper.

Usage:
  # From JSON string
  python3 scripts/insert_stock_db.py '{"code":"PBBANK","name":"Public Bank","industry":"Banking","lastPrice":4.71,"dividendYield":4.78,"peRatio":12.7,"roe":12.3,"debtToEquity":6.8,"marketCap":91.42,"score_composite":65,"score_subs":{"dividend":26,"growth":16,"quality":15,"risk":8},"status":"active","notes":"..."}'

  # With --sync flag to regenerate stocks.ts after insert
  python3 scripts/insert_stock_db.py --sync '<json>'
"""
import json, sys, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from db import get_db

TICKER_TO_SHORT = {
    '1155.KL': 'MAYBANK', '5106.KL': 'AXREIT', '6742.KL': 'YTLPOWR',
    '3379.KL': 'INSAS', '7089.KL': 'LIIHEN', '4731.KL': 'SCIENTEX',
    '0104.KL': 'GENETEC', '2445.KL': 'KLK', '0166.KL': 'INARI',
    '4197.KL': 'SIME', '7087.KL': 'MAGNI', '5983.KL': 'MBMR',
    '5293.KL': 'AME', '5132.KL': 'DELEUM', '5142.KL': 'WASCO',
    '5280.KL': 'KIPREIT', 'INTA.KL': 'INTA',
    '1066.KL': 'RHB', '7052.KL': 'PADINI',
    '5398.KL': 'GAMUDA', '5236.KL': 'MATRIX',
    '1295.KL': 'PBBANK', '5031.KL': 'TIME', '0099.KL': 'SCICOM',
    '5250.KL': 'SEM', '3255.KL': 'HEINEKEN',
}

SHORT_TO_TICKER = {v: k for k, v in TICKER_TO_SHORT.items()}

def main():
    sync = False
    args = sys.argv[1:]
    
    if '--sync' in args:
        sync = True
        args.remove('--sync')
    
    if not args:
        print("Usage: python3 scripts/insert_stock_db.py [--sync] '<json>'")
        sys.exit(1)
    
    data = json.loads(args[0])
    
    # Resolve ticker
    code = data.get('code', '')
    ticker = SHORT_TO_TICKER.get(code, code + '.KL')
    
    db = get_db()
    cur = db.cursor()
    
    cur.execute("""
        INSERT INTO stocks (id, name, industry, initial_price, status,
            score_composite, score_subs, last_price, price_change,
            dividend_yield, pe_ratio, roe, debt_to_equity, market_cap,
            sparkline, notes, kronos_warning, added_at, updated_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW(),NOW())
        ON CONFLICT (id) DO UPDATE SET
            name = EXCLUDED.name,
            industry = EXCLUDED.industry,
            score_composite = EXCLUDED.score_composite,
            score_subs = EXCLUDED.score_subs,
            last_price = EXCLUDED.last_price,
            price_change = EXCLUDED.price_change,
            dividend_yield = EXCLUDED.dividend_yield,
            pe_ratio = EXCLUDED.pe_ratio,
            roe = EXCLUDED.roe,
            debt_to_equity = EXCLUDED.debt_to_equity,
            market_cap = EXCLUDED.market_cap,
            sparkline = EXCLUDED.sparkline,
            notes = EXCLUDED.notes,
            kronos_warning = EXCLUDED.kronos_warning,
            status = EXCLUDED.status,
            updated_at = NOW()
    """, (
        ticker,
        data.get('name', ''),
        data.get('industry', ''),
        data.get('lastPrice', data.get('initial_price', 0)),
        data.get('status', 'revisit'),
        data.get('score_composite', 0),
        json.dumps(data.get('score_subs', {})),
        data.get('lastPrice', data.get('last_price', 0)),
        data.get('priceChange', data.get('price_change', 0)),
        data.get('dividendYield', data.get('dividend_yield', 0)),
        data.get('peRatio', data.get('pe_ratio', None)),
        data.get('roe', None),
        data.get('debtToEquity', data.get('debt_to_equity', None)),
        data.get('marketCap', data.get('market_cap', 0)),
        json.dumps(data.get('sparkline', [])),
        data.get('notes', ''),
        data.get('kronos_warning', None),
    ))
    
    db.commit()
    cur.close()
    db.close()
    
    print(f"  Inserted/updated: {ticker} ({code}) → status={data.get('status', 'revisit')}")
    
    if sync:
        sync_script = ROOT / 'scripts' / 'sync_from_db.py'
        subprocess.run([sys.executable, str(sync_script)], check=True)

if __name__ == '__main__':
    main()
