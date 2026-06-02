#!/usr/bin/env python3
"""Random deep analysis: pick 3 unanalyzed stocks, run Kronos + fundamentals + score, insert into stocks table.

Usage: python3 scripts/run_random_analysis.py [--count N]
"""
import sys, json, time, random
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.append(str(ROOT / 'Kronos'))

from db import get_db
from persona_db import SHORT_TO_TICKER as _ST

# Build reverse map for ticker→short
TICKER_TO_SHORT = {v: k for k, v in _ST.items()}

MYT = timezone(timedelta(hours=8))
PRED_LEN = 30
LOOKBACK = 200


def get_short_code(ticker):
    """Convert ticker to short code, or derive from number."""
    if ticker in TICKER_TO_SHORT:
        return TICKER_TO_SHORT[ticker]
    code = ticker.replace('.KL', '')
    return f'KLSE{code}'


def score_stock(dy_pct, pe, roe, de, rev_growth, mcap_b, kronos_pct):
    """Score a stock using the same formula as Deep Dive."""
    # Dividend (40% weight, cap 40)
    div = min(40, round(dy_pct * 5.5))
    
    # Growth (30% weight)
    growth = 15  # base
    if pe > 0 and pe < 15: growth += 8
    elif pe > 25: growth -= 5
    if rev_growth > 10: growth += 5
    if roe > 15: growth += 3
    growth = max(0, min(30, growth))
    
    # Quality (20% weight)
    quality = 12
    if roe > 20: quality += 4
    elif roe > 12: quality += 2
    if de < 1: quality += 3
    elif de > 50: quality -= 4
    quality = max(0, min(20, quality))
    
    # Risk (10% weight)
    risk = 7
    if mcap_b > 10: risk += 2
    elif mcap_b < 0.5: risk -= 2
    if kronos_pct < -10: risk -= 3
    elif kronos_pct < -5: risk -= 1
    risk = max(0, min(10, risk))
    
    return {
        'composite': div + growth + quality + risk,
        'dividend': div, 'growth': growth, 'quality': quality, 'risk': risk,
    }


def run_analysis(count=3, process_pending=False):
    """Run deep analysis on random unanalyzed stocks (or pending queue)."""
    from model import Kronos, KronosTokenizer, KronosPredictor
    
    db = get_db()
    cur = db.cursor()
    
    # Load Kronos
    print("Loading Kronos...", flush=True)
    tokenizer = KronosTokenizer.from_pretrained("NeoQuasar/Kronos-Tokenizer-base")
    model = Kronos.from_pretrained("NeoQuasar/Kronos-small")
    predictor = KronosPredictor(model, tokenizer, device="cpu", max_context=512)
    
    # Get targets
    if process_pending:
        cur.execute("SELECT stock_code FROM pending_analyses WHERE processed = FALSE ORDER BY requested_at LIMIT %s", (count,))
        targets = [(r[0], get_short_code(r[0])) for r in cur.fetchall()]
    else:
        cur.execute("SELECT stock_code, name FROM bursa_universe WHERE has_analysis = FALSE ORDER BY RANDOM() LIMIT %s", (count,))
        targets = [(r[0], get_short_code(r[0])) for r in cur.fetchall()]
    
    if not targets:
        print("No unanalyzed stocks found")
        cur.close(); db.close()
        return []
    
    print(f"Analyzing {len(targets)} stocks...")
    
    import yfinance as yf
    results = []
    
    for ticker, short_name in targets:
        print(f"\n{short_name} ({ticker})...", flush=True)
        
        try:
            t = yf.Ticker(ticker)
            info = t.info
            hist = t.history(period='1y')
            
            if len(hist) < 50:
                print(f"  SKIP: only {len(hist)} data points")
                continue
            
            price = float(hist['Close'].iloc[-1])
            pe = info.get('trailingPE') or info.get('forwardPE') or 0
            dy_pct = round((info.get('dividendYield') or 0) * 100, 2)
            roe = round((info.get('returnOnEquity') or 0) * 100, 2)
            de = info.get('debtToEquity') or 0
            mcap = info.get('marketCap') or 0
            mcap_b = round(mcap / 1e9, 2)
            rev_growth = round((info.get('revenueGrowth') or 0) * 100, 2)
            name = info.get('longName') or info.get('shortName') or short_name
            industry = info.get('industry') or ''
            
            # Normalize yfinance quirks
            if dy_pct > 100:
                dy_pct = dy_pct / 100  # yfinance sometimes returns already-scaled
            if pe > 1000:
                pe = 0  # data error
            
            print(f"  P={price:.2f} PE={pe:.1f} DY={dy_pct:.1f}% ROE={roe:.1f}% D/E={de:.1f} RevG={rev_growth:.1f}%", flush=True)
            
            # Kronos
            records = []
            for idx, row in hist.iterrows():
                records.append({
                    'date': idx.strftime('%Y-%m-%d'), 'open': float(row['Open']),
                    'high': float(row['High']), 'low': float(row['Low']),
                    'close': float(row['Close']), 'volume': int(row['Volume']),
                })
            df = pd.DataFrame(records)
            df['date'] = pd.to_datetime(df['date'])
            
            x_df = df.iloc[-LOOKBACK:][['open', 'high', 'low', 'close']].reset_index(drop=True)
            x_timestamp = df.iloc[-LOOKBACK:]['date'].reset_index(drop=True)
            
            last_date = df['date'].iloc[-1]
            future_dates = []
            d = last_date + timedelta(days=1)
            while len(future_dates) < PRED_LEN:
                if d.weekday() < 5:
                    future_dates.append(d)
                d += timedelta(days=1)
            y_timestamp = pd.Series(future_dates)
            
            pred_df = predictor.predict(df=x_df, x_timestamp=x_timestamp, y_timestamp=y_timestamp,
                                        pred_len=PRED_LEN, T=1.0, top_p=0.9, sample_count=1, verbose=False)
            
            last_close = x_df['close'].iloc[-1]
            pred_close = pred_df['close'].values
            kronos_pct = round((pred_close[-1] - last_close) / last_close * 100, 2)
            
            sign = '+' if kronos_pct > 0 else ''
            print(f"  Kronos: RM{last_close:.2f} → RM{pred_close[-1]:.2f} ({sign}{kronos_pct:.1f}%)", flush=True)
            
            # Score
            scores = score_stock(dy_pct, pe, roe, de, rev_growth, mcap_b, kronos_pct)
            status = 'active' if scores['composite'] >= 70 else 'revisit'
            kronos_warning = None
            if kronos_pct <= -10:
                kronos_warning = f'STRONG BEARISH {kronos_pct:+.1f}%'
            elif kronos_pct <= -5:
                kronos_warning = f'BEARISH {kronos_pct:+.1f}%'
            
            notes = f'P/E {pe:.1f}x, DY {dy_pct:.1f}%, ROE {roe:.1f}%, D/E {de:.1f}. Kronos {kronos_pct:+.1f}%.'
            if kronos_warning:
                notes = f'⚠️ {kronos_warning}. ' + notes
            
            # Insert into stocks table
            cur.execute('''
                INSERT INTO stocks (id, name, industry, initial_price, status,
                    score_composite, score_subs, last_price, dividend_yield, pe_ratio,
                    roe, debt_to_equity, market_cap, notes, kronos_warning, added_at, updated_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW(),NOW())
                ON CONFLICT (id) DO UPDATE SET
                    score_composite=EXCLUDED.score_composite, score_subs=EXCLUDED.score_subs,
                    last_price=EXCLUDED.last_price, dividend_yield=EXCLUDED.dividend_yield,
                    pe_ratio=EXCLUDED.pe_ratio, roe=EXCLUDED.roe, debt_to_equity=EXCLUDED.debt_to_equity,
                    market_cap=EXCLUDED.market_cap, notes=EXCLUDED.notes,
                    kronos_warning=EXCLUDED.kronos_warning, status=EXCLUDED.status,
                    updated_at=NOW()
            ''', (ticker, name, industry, price, status, scores['composite'],
                  json.dumps(scores), price, dy_pct, pe, roe, de, mcap_b, notes, kronos_warning))
            
            # Mark as analyzed in universe
            cur.execute("UPDATE bursa_universe SET has_analysis=TRUE, last_analyzed_at=NOW() WHERE stock_code=%s", (ticker,))
            
            # Mark pending as processed
            if process_pending:
                cur.execute("UPDATE pending_analyses SET processed=TRUE, processed_at=NOW() WHERE stock_code=%s", (ticker,))
            
            result = {
                'ticker': ticker, 'short': short_name, 'name': name,
                'price': price, 'score': scores['composite'], 'status': status,
                'kronos_pct': kronos_pct, 'dy': dy_pct, 'pe': pe, 'roe': roe,
            }
            results.append(result)
            print(f"  Score: {scores['composite']} → {status}", flush=True)
            
        except Exception as e:
            print(f"  ERROR: {e}")
            # Mark as analyzed anyway to avoid retrying bad tickers
            cur.execute("UPDATE bursa_universe SET has_analysis=TRUE WHERE stock_code=%s", (ticker,))
    
    db.commit()
    cur.close()
    db.close()
    return results


if __name__ == '__main__':
    count = 3
    process = '--pending' in sys.argv
    for i, arg in enumerate(sys.argv):
        if arg == '--count':
            count = int(sys.argv[i+1])
    
    results = run_analysis(count, process_pending=process)
    
    if results:
        print(f"\n{'='*50}")
        print("RESULTS")
        print(f"{'='*50}")
        for r in results:
            sign = '▲' if r['kronos_pct'] > 0 else '▼'
            print(f"  {r['short']:10s} {r['name'][:30]:30s} score={r['score']:3d} {r['status']:8s} {sign} Kronos {r['kronos_pct']:+.1f}%")
        
        # Trigger sync + deploy
        import subprocess
        subprocess.run([sys.executable, str(ROOT / 'scripts' / 'sync_from_db.py')], check=True)
        subprocess.run(['npm', 'run', 'build'], cwd=str(ROOT / 'web'), check=True)
        subprocess.run(['npx', 'sst', 'deploy', '--stage', 'live'], cwd=str(ROOT))
        print("✓ Deployed")
