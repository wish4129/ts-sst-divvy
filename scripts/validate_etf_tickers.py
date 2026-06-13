#!/usr/bin/env python3
"""Phase 1: Bursa ETF Ticker Compilation & yfinance Validation
Run: python3 scripts/validate_etf_tickers.py [--verify]

Scrapes known Bursa Malaysia ETF list (or uses compiled list),
validates yfinance data availability, outputs summary.
"""

import sys
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from db import get_db

# Known Bursa ETFs (compiled from bursamalaysia.com ETF list)
# Format: (ticker_suffix, name, category, shariah_flag)
BURSA_ETFS = [
    # Equity ETFs
    ("0820EA", "FBM KLCI ETF (0820EA)", "Equity", True),         # FBM KLCI tracker
    ("0821EA", "MYETF DOW JONES ISLAMIC MARKET MY", "Equity", True),
    ("0822EA", "MYETF Asean 40", "Equity", False),
    ("5097",   "MYETF Shariah 100 (R)", "Equity", True),
    ("5098",   "MYETF Shariah 100 (USD)", "Equity", True),
    ("5124",   "MYETF MSCI MALAYSIA ISLAMIC DIVIDEND", "Equity", True),
    ("5125",   "MYETF MSCI MALAYSIA ISLAMIC DIVIDEND (USD)", "Equity", True),
    ("5136",   "MYETF S&P 500 SHARIAH (MYR)", "Equity", True),
    ("5137",   "MYETF S&P 500 SHARIAH (USD)", "Equity", True),
    ("5138",   "MYETF S&P 500 SHARIAH (LB)", "Equity", True),
    
    # REIT ETFs
    ("5130",   "MYETF Shariah Asia Pacific ex-Jpn REIT", "REIT", True),
    ("5131",   "MYETF Shariah Asia Pacific ex-Jpn REIT (USD)", "REIT", True),
    ("5123",   "MYETF Shariah Asia Pacific ex-Jpn REIT (LB)", "REIT", True),
    
    # Commodity/Gold ETFs
    ("0820EA", "TradePlus Shariah Gold Tracker", "Gold", True),
    
    # Bond/Sukuk
    ("5294",   "MYETF Shariah Sukuk ETF", "Bond", True),
    
    # Leveraged/Inverse
    ("5128",   "TradePlus S&P 500 Shariah 2xL (MYR)", "Leveraged/Inverse", True),
    ("5129",   "TradePlus S&P 500 Shariah 2xL (USD)", "Leveraged/Inverse", True),
    
    # Others
    ("5144",   "MYETF MSCI South East Asia", "Equity", False),
]

def validate_yfinance(ticker_code):
    """Check if yfinance has data for this ticker."""
    try:
        import yfinance as yf
        t = yf.Ticker(ticker_code)
        info = t.info
        if info and info.get("regularMarketPrice") is not None:
            return {
                "available": True,
                "price": info.get("regularMarketPrice"),
                "name": info.get("longName", info.get("shortName", "")),
                "category": info.get("category", ""),
                "expense_ratio": info.get("annualReportExpenseRatio"),
                "aum": info.get("totalAssets"),
                "yield_pct": info.get("yield"),
                "return_1y": None,  # yfinance doesn't reliably provide this historically
            }
        return {"available": False, "reason": "No price data"}
    except Exception as e:
        return {"available": False, "reason": str(e)}

def main():
    print("=" * 60)
    print("Bursa ETF yfinance Validation")
    print("=" * 60)
    
    results = {"valid": [], "failed": [], "total": len(BURSA_ETFS)}
    
    for suffix, name, category, shariah in BURSA_ETFS:
        ticker = f"{suffix}.KL" if not suffix.endswith(".KL") else suffix
        print(f"  {ticker:20s} {name[:40]:40s}...", end=" ", flush=True)
        
        result = validate_yfinance(ticker)
        if result["available"]:
            print(f"✓ RM{result['price']:.2f}" if result["price"] else "✓ (data available)")
            results["valid"].append({
                "ticker": ticker,
                "name": name,
                "category": category,
                "shariah": shariah,
                "price": result.get("price"),
                "expense_ratio": result.get("expense_ratio"),
                "aum": result.get("aum"),
            })
        else:
            print(f"✗ {result.get('reason', 'unknown')}")
            results["failed"].append({
                "ticker": ticker,
                "name": name,
                "reason": result.get("reason", "unknown"),
            })
        
        time.sleep(0.3)  # Rate limit
    
    print(f"\n{'=' * 60}")
    print(f"Valid ETF tickers: {len(results['valid'])}/{results['total']}")
    print(f"Failed: {len(results['failed'])}/{results['total']}")
    
    if results["failed"]:
        print(f"\nFailed tickers:")
        for f in results["failed"]:
            print(f"  {f['ticker']:20s} {f['name'][:40]:40s} — {f['reason']}")
    
    # Save results
    output = ROOT / "data" / "etf_tickers.json"
    output.write_text(json.dumps(results, indent=2, default=str))
    print(f"\nResults saved to {output}")


if __name__ == "__main__":
    main()
