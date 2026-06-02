#!/usr/bin/env python3
"""Batch scrape Bursa stock prices from KLSE Screener."""
import asyncio
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

# Get stock list from portfolios.json
pf = json.loads((ROOT / "scripts" / "portfolios.json").read_text())

async def fetch_price(sem, code: str, short: str, name: str) -> tuple[str, float]:
    """Fetch a single stock price from KLSE Screener."""
    ticker = code.replace('.KL', '')
    url = f"https://www.klsescreener.com/v2/stocks/view/{ticker}"
    
    proc = await asyncio.create_subprocess_exec(
        'curl', '-sL', '-A',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        url,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL
    )
    stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
    html = stdout.decode('utf-8', errors='replace')
    
    price = 0.0
    
    # Find all decimal numbers that look like stock prices
    prices = re.findall(r'(\d+\.\d{3})', html)
    if prices:
        price = float(prices[0])
    
    return short, price

async def main():
    sem = asyncio.Semaphore(5)
    tasks = []
    for short, info in pf['stocks'].items():
        tasks.append(fetch_price(sem, info['code'], short, info['name']))
    
    results = await asyncio.gather(*tasks)
    
    prices = {}
    for short, price in results:
        prices[short] = price
        print(f"  {short:>8}: RM{price:>7.3f}")
    
    out_path = ROOT / "data" / "live_prices.json"
    out_path.write_text(json.dumps(prices, indent=2) + "\n")
    print(f"\nSaved {len(prices)} prices to {out_path}")

if __name__ == "__main__":
    asyncio.run(main())
