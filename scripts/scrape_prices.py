#!/usr/bin/env python3
"""Scrape live Bursa stock prices from KLSE Screener for Divvy portfolio battle.

Usage:
    cd ~/xiongit/divvy
    uv run scripts/scrape_prices.py    # if uv project
    .venv/bin/python3 scripts/scrape_prices.py  # if venv

Output: data/live_prices.json as {short_name: price_float}
Uses: scrapling CLI (extract get) for TLS fingerprinting.
All stocks use numeric Bursa codes — INTA uses 0192, not "INTA".
"""

import json
import re
import subprocess
import sys
import tempfile
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Short name → Bursa numeric code
# ALL codes are the numeric part of Bursa's stock code
# INTA is 0192, not "INTA" (ACE Market stocks use numeric codes too)
STOCK_CODES = {
    'MAYBANK': '1155', 'AXREIT': '5106', 'YTLPOWR': '6742',
    'INSAS': '3379', 'LIIHEN': '7089', 'SCIENTEX': '4731',
    'GENETEC': '0104', 'KLK': '2445', 'INARI': '0166',
    'SIME': '4197', 'MAGNI': '7087', 'MBMR': '5983',
    'AME': '5293', 'DELEUM': '5132', 'WASCO': '5142',
    'KIPREIT': '5280', 'INTA': '0192',
    'RHB': '1066', 'PADINI': '7052',
    'GAMUDA': '5398', 'MATRIX': '5236',
    'PBBANK': '1295', 'TIME': '5031', 'SCICOM': '0099',
    'SEM': '5250',
}

BASE_URL = 'https://www.klsescreener.com/v2/stocks/view'

def find_scrapling():
    """Locate the scrapling binary."""
    candidates = [
        os.path.expanduser('~/.local/bin/scrapling'),
        '/usr/local/bin/scrapling',
        'scrapling',  # may be in PATH somewhere
    ]
    for c in candidates:
        if os.path.isfile(c) or c == 'scrapling':
            # check if it runs
            try:
                subprocess.run([c, '--help'], capture_output=True, timeout=5)
                return c
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
    return None

def scrape_price(code: str, scrapling_bin: str) -> float | None:
    """Scrape a single stock price from KLSE Screener."""
    url = f'{BASE_URL}/{code}'
    tmp = tempfile.mktemp(suffix='.html')

    try:
        result = subprocess.run(
            [scrapling_bin, 'extract', 'get', url, tmp],
            capture_output=True, timeout=30, text=True
        )
        if result.returncode != 0:
            print(f"  [{code}] scrapling error: {result.stderr.strip()[:200]}")
            return None

        html = Path(tmp).read_text()
        m = re.search(r'<span[^>]*id="price"[^>]*data-value="([^\"]+)"', html)
        if m:
            price = float(m.group(1))
            print(f"  [{code}] RM {price:.4f}")
            return price
        else:
            print(f"  [{code}] price element not found")
            return None
    except subprocess.TimeoutExpired:
        print(f"  [{code}] timeout")
        return None
    except Exception as e:
        print(f"  [{code}] error: {e}")
        return None
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass

def main():
    scrapling_bin = find_scrapling()
    if not scrapling_bin:
        print("ERROR: scrapling CLI not found.", file=sys.stderr)
        print("Install: uv tool install scrapling && scrapling install", file=sys.stderr)
        sys.exit(1)

    print(f"Scraping {len(STOCK_CODES)} stock prices from KLSE Screener...")
    print(f"  Using: {scrapling_bin}")
    prices = {}

    for i, (name, code) in enumerate(STOCK_CODES.items(), 1):
        print(f"[{i}/{len(STOCK_CODES)}] {name} ({code})...", end=' ', flush=True)
        price = scrape_price(code, scrapling_bin)
        if price is not None:
            prices[name] = price
        else:
            print(f"  ⚠ {name}: failed")
        time.sleep(1)  # polite delay

    # Load existing to fill any gaps
    existing_path = ROOT / 'data' / 'live_prices.json'
    if existing_path.exists():
        existing = json.loads(existing_path.read_text())
        for name in STOCK_CODES:
            if name not in prices and name in existing:
                prices[name] = existing[name]
                print(f"  ↻ {name}: kept previous RM {existing[name]:.4f}")

    # Write output (flat format: {name: float})
    output_path = ROOT / 'data' / 'live_prices.json'
    output_path.write_text(json.dumps(prices, indent=2) + '\n')

    failed = set(STOCK_CODES.keys()) - set(prices.keys())
    print(f"\n✓ Saved {len(prices)} prices to data/live_prices.json")
    if failed:
        print(f"  Failed: {failed}")
    return 0 if not failed else 1

if __name__ == '__main__':
    sys.exit(main())
