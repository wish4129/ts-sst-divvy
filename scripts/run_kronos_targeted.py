#!/usr/bin/env python3
"""Targeted Kronos forecast runner — runs for specific tickers only.

Usage (CLI):
  python3 scripts/run_kronos_targeted.py TICKER1 TICKER2 ...
  python3 scripts/run_kronos_targeted.py --force TICKER1 TICKER2 ...

Import (module):
  from run_kronos_targeted import run_forecast
  results = run_forecast(['1155.KL', '6742.KL'], force=False)
"""
import pandas as pd
import numpy as np
import sys, json, time, os, signal
from datetime import datetime, timedelta
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "Kronos"))
from model import Kronos, KronosTokenizer, KronosPredictor

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from db import get_db, dict_cursor

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

class KronosLoadTimeout(Exception):
    pass

def _on_alarm(signum, frame):
    raise KronosLoadTimeout("Kronos loading timed out")


def run_forecast(tickers, force=False):
    """Run Kronos forecasts for the given tickers.

    Args:
        tickers: List of stock ticker IDs (e.g. ['1155.KL', '6742.KL'])
        force: If True, skip the stock_prices pre-filter check

    Returns:
        dict: {stock_name: forecast_data} — same format as the JSON output.
              Keys with 'error' subdicts indicate failures.
    """
    if not tickers:
        print("run_forecast: no tickers provided", flush=True)
        return {}

    print(f"Targeting {len(tickers)} stocks: {', '.join(tickers)}", flush=True)

    MIN_PRICE_ROWS = 200

    # Fetch stock details from DB
    db = get_db()
    cur = dict_cursor(db)
    cur.execute(
        "SELECT id, name FROM stocks WHERE id = ANY(%s) AND status NOT IN ('removed', 'data_missing')",
        (tickers,)
    )
    all_stocks = [(r['name'], r['id']) for r in cur.fetchall()]
    cur.close()
    db.close()

    if force:
        stocks = all_stocks
        print("--force: skipping price-history pre-filter, running all stocks even with < 200 rows", flush=True)
    else:
        # Query price history counts for all candidate stocks
        stock_ids = [s[1] for s in all_stocks]
        if stock_ids:
            db2 = get_db()
            cur2 = dict_cursor(db2)
            cur2.execute(
                "SELECT stock_id, COUNT(*)::int AS cnt FROM stock_prices "
                "WHERE stock_id = ANY(%s) GROUP BY stock_id",
                (stock_ids,)
            )
            price_counts = {r['stock_id']: r['cnt'] for r in cur2.fetchall()}
            cur2.close()
            db2.close()
        else:
            price_counts = {}

        stocks = []
        skipped = []
        for name, sid in all_stocks:
            cnt = price_counts.get(sid, 0)
            if cnt >= MIN_PRICE_ROWS:
                stocks.append((name, sid))
            else:
                skipped.append((name, sid, cnt))

        if skipped:
            print(f"PRE-FILTER: skipped {len(skipped)} stock(s) with < {MIN_PRICE_ROWS} price rows:", flush=True)
            for name, sid, cnt in skipped:
                print(f"  SKIP {name} ({sid}): only {cnt} rows in stock_prices", flush=True)

        if not stocks:
            print("No qualifying stocks with sufficient price history (>= 200 rows)", flush=True)
            return {}

    print(f"Loading Kronos-small for {len(stocks)} qualifying stocks...", flush=True)
    t0 = time.time()
    signal.signal(signal.SIGALRM, _on_alarm)
    signal.alarm(30)
    try:
        tokenizer = KronosTokenizer.from_pretrained("NeoQuasar/Kronos-Tokenizer-base")
        model = Kronos.from_pretrained("NeoQuasar/Kronos-small")
    finally:
        signal.alarm(0)
    print(f"  Model loaded in {time.time()-t0:.1f}s", flush=True)

    predictor = KronosPredictor(model, tokenizer, device="cpu", max_context=512)

    print(f"Forecasting {len(stocks)} stocks", flush=True)

    LOOKBACK = 200
    PRED_LEN = 30
    results = {}

    import yfinance as yf

    for stock_name, ticker in stocks:
        print(f"\n{stock_name} ({ticker})...", flush=True)
        t = yf.Ticker(ticker)
        hist = t.history(period='1y')

        if len(hist) < LOOKBACK:
            print(f"  SKIP: only {len(hist)} rows", flush=True)
            continue

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
        df = df.dropna(subset=['open', 'high', 'low', 'close'])

        if len(df) < LOOKBACK:
            print(f"  SKIP: only {len(df)} clean rows (need {LOOKBACK})", flush=True)
            continue

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
            print(f"  RM{last_close:.2f} -> RM{pred_close[-1]:.2f} ({sign}{pred_change:.1f}%) in {elapsed:.1f}s", flush=True)

        except Exception as e:
            print(f"  ERROR: {e}", flush=True)
            results[stock_name] = {'ticker': ticker, 'error': str(e)}

    return results


def write_results(results, output_path=None):
    """Save forecast results to JSON and Supabase.

    Args:
        results: dict from run_forecast()
        output_path: Path to save JSON (default: data/kronos_forecast.json)
    """
    if output_path is None:
        output_path = ROOT / 'data' / 'kronos_forecast.json'

    # Save JSON
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n{'='*50}")
    print("FORECAST SUMMARY")
    print(f"{'='*50}")
    for name, r in results.items():
        if 'error' in r:
            print(f"  {name}: ERROR - {r['error']}")
        else:
            pred_change = r['pred_change_pct']
            sign = '+' if pred_change > 0 else ''
            arrow = chr(9650) if pred_change > 0 else chr(9660)  # ▲ or ▼ without emoji
            print(f"  {arrow} {name}: RM{r['last_close']:.2f} -> RM{r['pred_30d_close']:.2f} ({sign}{pred_change:.1f}%) vol={r['pred_volatility']}%")
    print(f"\nSaved to {output_path}")

    # Write to Supabase
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
                (r['ticker'], float(r['pred_30d_close']), float(r['pred_change_pct']),
                 float(r['pred_low']), float(r['pred_high']), float(r['pred_volatility'])))
            inserted += 1
        db.commit()
        cur.close()
        db.close()
        print(f"[OK] Wrote {inserted} forecasts to Supabase (kronos_forecasts)")
    except Exception as e:
        print(f"[SKIP] Supabase write skipped: {e}")


def main():
    """CLI entry point."""
    tickers = [a.strip() for a in sys.argv[1:] if a.strip()]
    if not tickers:
        print("Usage: python3 scripts/run_kronos_targeted.py [--force] TICKER1 TICKER2 ...")
        sys.exit(1)

    force = False
    if "--force" in tickers:
        force = True
        tickers.remove("--force")

    results = run_forecast(tickers, force=force)
    write_results(results)


if __name__ == '__main__':
    main()
