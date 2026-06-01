"""Daily macro signal fetcher — yfinance (free, no API key needed).

Fetches: Brent crude, CPO, USD/MYR, FBMKLCI, SOX index, FBX shipping.
Output: data/macro_signals.json (latest snapshot)
         data/macro_history.json (time series, appended)

Usage: python3 scripts/macro_fetcher.py
Cron: 0 7 * * 1-5  (weekday mornings before market open)
"""
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

MALAYSIA_TZ = timezone(timedelta(hours=8))

try:
    import yfinance as yf
    import pandas as pd
except ImportError:
    print("Installing yfinance...")
    import os; os.system(f"{sys.executable} -m pip install yfinance --quiet")
    import yfinance as yf
    import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SIGNALS_PATH = ROOT / "data" / "macro_signals.json"
HISTORY_PATH = ROOT / "data" / "macro_history.json"

# ── Macro tickers ──
INDICATORS = {
    "brent_crude": {
        "ticker": "BZ=F",
        "label": "Brent Crude Oil",
        "unit": "USD/bbl",
        "category": "commodity",
    },
    "cpo": {
        "ticker": "2445.KL",  # KL Kepong — best CPO proxy on KLSE
        "label": "CPO Price Proxy (KLK)",
        "unit": "MYR/share",
        "category": "commodity",
        "note": "KL Kepong is the purest CPO play. For actual CPO price, scrape MPOB.",
    },
    "usd_myr": {
        "ticker": "MYR=X",
        "label": "USD/MYR",
        "unit": "MYR per USD",
        "category": "fx",
    },
    "fb_klci": {
        "ticker": "^KLSE",
        "label": "FBM KLCI",
        "unit": "index",
        "category": "equity",
    },
    "sox_index": {
        "ticker": "^SOX",
        "label": "Philadelphia Semiconductor Index",
        "unit": "index",
        "category": "equity",
    },
    "fbx_shipping": {
        "ticker": "2445.KL",  # KLK as shipping proxy — FBX not on yfinance
        "label": "Freightos Baltic Index (NOT AVAILABLE)",
        "unit": "",
        "category": "shipping",
        "optional": True,
        "disabled": True,
    },
    "snp500": {
        "ticker": "^GSPC",
        "label": "S&P 500",
        "unit": "index",
        "category": "equity",
    },
    "china_pmi": {
        "ticker": "FXI",  # FTSE China 50 ETF — proxy
        "label": "FTSE China 50 (PMI proxy)",
        "unit": "index",
        "category": "equity",
        "optional": True,
    },
    "steel_price": {
        "ticker": "SLX",  # Steel ETF — proxy
        "label": "Steel ETF (price proxy)",
        "unit": "USD",
        "category": "commodity",
        "optional": True,
    },
}

# ── Fetch ──
now = datetime.now(MALAYSIA_TZ)
date_str = now.strftime("%Y-%m-%d")
timestamp = now.strftime("%Y-%m-%dT%H:%M:%S+08:00")

print(f"[{timestamp}] Fetching macro signals...")

signals = {}
errors = []

tickers = {k: v["ticker"] for k, v in INDICATORS.items() if not v.get("disabled")}
ticker_list = list(tickers.values())

try:
    data = yf.download(ticker_list, period="5d", progress=False, auto_adjust=True)
except Exception as e:
    print(f"  yfinance download failed: {e}")
    print(f"  Tickers: {ticker_list}")
    sys.exit(1)

# Handle single vs multi ticker return
if len(ticker_list) == 1:
    data.columns = pd.MultiIndex.from_product([data.columns, ticker_list])

for key, info in INDICATORS.items():
    ticker = info["ticker"]
    try:
        if ticker in data["Close"].columns:
            close_series = data["Close"][ticker].dropna()
            if len(close_series) >= 2:
                latest = float(close_series.iloc[-1])
                prev_close = float(close_series.iloc[-2])
                change_pct = ((latest - prev_close) / prev_close) * 100 if prev_close else 0

                # Trend: 5d simple
                trend_5d = ((latest - float(close_series.iloc[0])) / float(close_series.iloc[0])) * 100 if len(close_series) >= 3 else 0

                signals[key] = {
                    "label": info["label"],
                    "unit": info["unit"],
                    "value": round(latest, 4),
                    "change_pct": round(change_pct, 2),
                    "trend_5d_pct": round(trend_5d, 2),
                    "trend": "up" if trend_5d > 1 else "down" if trend_5d < -1 else "flat",
                    "category": info["category"],
                }
                direction = "▲" if change_pct > 0 else "▼" if change_pct < 0 else "—"
                print(f"  {direction} {info['label']:30s} {latest:>10.4f} {info['unit']:15s} ({change_pct:+.2f}%)")
            else:
                errors.append(f"{key}: insufficient data ({len(close_series)} points)")
        else:
            if not info.get("optional"):
                errors.append(f"{key}: no data for {ticker}")
    except Exception as e:
        if not info.get("optional"):
            errors.append(f"{key}: {e}")

# ── Derived signals ──

if "fb_klci" in signals:
    val = signals["fb_klci"]["value"]
    if val >= 1650:
        regime = "bull"
    elif val >= 1500:
        regime = "sideways"
    else:
        regime = "bear"
    signals["klci_regime"] = {
        "label": "KLCI Market Regime",
        "unit": "categorical",
        "value": regime,
        "change_pct": 0,
        "trend_5d_pct": 0,
        "trend": regime,
        "category": "regime",
    }
    print(f"  ℹ  KLCI Regime: {regime} (index={val:.0f})")

# ── Save ──
output = {
    "date": date_str,
    "timestamp": timestamp,
    "signals": signals,
    "errors": errors,
}

SIGNALS_PATH.parent.mkdir(parents=True, exist_ok=True)
SIGNALS_PATH.write_text(json.dumps(output, indent=2))
print(f"\n✓ Saved {len(signals)} signals to {SIGNALS_PATH}")

# ── Append to history ──
history = []
if HISTORY_PATH.exists():
    try:
        history = json.loads(HISTORY_PATH.read_text())
    except Exception:
        pass

history.append(output)
if len(history) > 365:
    history = history[-365:]  # keep 1 year

HISTORY_PATH.write_text(json.dumps(history, indent=2))
print(f"✓ Appended to {HISTORY_PATH} ({len(history)} days)")

if errors:
    print(f"\n⚠ {len(errors)} errors:")
    for e in errors:
        print(f"  - {e}")
