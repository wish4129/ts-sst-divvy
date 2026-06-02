import pandas as pd
import numpy as np
import sys, json, time
from datetime import datetime, timedelta
from pathlib import Path

sys.path.append("./Kronos/")
from model import Kronos, KronosTokenizer, KronosPredictor

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))
from db import get_db, dict_cursor

# --- Load model ---
print("Loading Kronos-small...", flush=True)
t0 = time.time()
tokenizer = KronosTokenizer.from_pretrained("NeoQuasar/Kronos-Tokenizer-base")
model = Kronos.from_pretrained("NeoQuasar/Kronos-small")
print(f"  Model loaded in {time.time()-t0:.1f}s", flush=True)

predictor = KronosPredictor(model, tokenizer, device="cpu", max_context=512)

# --- Read stocks from DB (source of truth) ---
sys.path.insert(0, str(ROOT / "scripts"))
from db import get_db, dict_cursor

db = get_db()
cur = dict_cursor(db)
cur.execute("SELECT name, id FROM stocks WHERE status != 'removed' ORDER BY name")
stocks = [(r['name'], r['id']) for r in cur.fetchall()]
cur.close()
db.close()
print(f"Forecasting {len(stocks)} stocks from DB")

LOOKBACK = 200  # trading days of context
PRED_LEN = 30   # trading days to predict (~6 weeks)

results = {}

for stock_name, ticker in stocks:
    print(f"\n{stock_name} ({ticker})...", flush=True)
    
    # Fetch data from yfinance directly
    import yfinance as yf
    t = yf.Ticker(ticker)
    hist = t.history(period='1y')
    
    if len(hist) < LOOKBACK:
        print(f"  SKIP: only {len(hist)} rows")
        continue
    
    # Build DataFrame
    records = []
    for idx, row in hist.iterrows():
        records.append({
            'date': idx.strftime('%Y-%m-%d'),
            'open': float(row['Open']),
            'high': float(row['High']),
            'low': float(row['Low']),
            'close': float(row['Close']),
            'volume': int(row['Volume']),
        })
    df = pd.DataFrame(records)
    df['date'] = pd.to_datetime(df['date'])
    
    # Use last LOOKBACK days as input
    x_df = df.iloc[-LOOKBACK:][['open', 'high', 'low', 'close']].reset_index(drop=True)
    x_timestamp = df.iloc[-LOOKBACK:]['date'].reset_index(drop=True)
    
    # Generate future trading day timestamps (skip weekends)
    last_date = df['date'].iloc[-1]
    future_dates = []
    d = last_date + timedelta(days=1)
    while len(future_dates) < PRED_LEN:
        if d.weekday() < 5:  # Mon-Fri
            future_dates.append(d)
        d += timedelta(days=1)
    y_timestamp = pd.Series(future_dates)
    
    t1 = time.time()
    try:
        pred_df = predictor.predict(
            df=x_df,
            x_timestamp=x_timestamp,
            y_timestamp=y_timestamp,
            pred_len=PRED_LEN,
            T=1.0,
            top_p=0.9,
            sample_count=1,
            verbose=False
        )
        elapsed = time.time() - t1
        
        # Summary stats
        last_close = x_df['close'].iloc[-1]
        pred_close = pred_df['close'].values
        pred_change = (pred_close[-1] - last_close) / last_close * 100
        pred_min = pred_close.min()
        pred_max = pred_close.max()
        
        results[stock_name] = {
            'ticker': ticker,
            'last_close': round(last_close, 4),
            'pred_30d_close': round(float(pred_close[-1]), 4),
            'pred_change_pct': round(pred_change, 2),
            'pred_low': round(float(pred_min), 4),
            'pred_high': round(float(pred_max), 4),
            'pred_volatility': round(float(np.std(pred_close) / last_close * 100), 2),
            'time_s': round(elapsed, 1),
        }
        
        sign = '+' if pred_change > 0 else ''
        print(f"  RM{last_close:.2f} → RM{pred_close[-1]:.2f} ({sign}{pred_change:.1f}%) in {elapsed:.1f}s")
        
    except Exception as e:
        print(f"  ERROR: {e}")
        results[stock_name] = {'ticker': ticker, 'error': str(e)}

# --- Save JSON (backward compat) ---
with open('data/kronos_forecast.json', 'w') as f:
    json.dump(results, f, indent=2)

print(f"\n{'='*50}")
print("FORECAST SUMMARY")
print(f"{'='*50}")
for name, r in results.items():
    if 'error' in r:
        print(f"  {name}: ERROR - {r['error']}")
    else:
        sign = '▲' if r['pred_change_pct'] > 0 else '▼'
        print(f"  {sign} {name}: RM{r['last_close']:.2f} → RM{r['pred_30d_close']:.2f} ({r['pred_change_pct']:+.1f}%) vol={r['pred_volatility']}%")
print(f"\nSaved to data/kronos_forecast.json")

# --- Write to Supabase ---
try:
    db = get_db()
    cur = dict_cursor(db)
    inserted = 0
    for name, r in results.items():
        if 'error' in r:
            continue
        cur.execute(
            """INSERT INTO kronos_forecasts (stock_id, pred_30d_close, pred_change_pct,
               pred_low, pred_high, pred_volatility)
               VALUES (%s,%s,%s,%s,%s,%s)""",
            (r['ticker'], r['pred_30d_close'], r['pred_change_pct'],
             r['pred_low'], r['pred_high'], r['pred_volatility']))
        inserted += 1
    db.commit()
    cur.close()
    db.close()
    print(f"✓ Wrote {inserted} forecasts to Supabase (kronos_forecasts)")
except Exception as e:
    print(f"⚠ Supabase write skipped: {e}")
    print(f"  (DB_PASSWORD env var may not be set — JSON file is still saved)")
