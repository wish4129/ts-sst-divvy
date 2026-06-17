#!/usr/bin/env python3
"""Dividend declaration data scraper — i3investor News → Supabase stocks.dividends JSONB.

Scrapes https://klse.i3investor.com/ for dividend news items, parses each
detail page (announce date, subject, amount, ex-date, payment date), matches
the stock ticker to our DB, and appends to stocks.dividends JSONB column.

Usage:
    python3 scripts/dividend_scraper.py                   # scrape all news
    python3 scripts/dividend_scraper.py --news-only       # only list news, no DB writes
    python3 scripts/dividend_scraper.py --max-news 3      # scrape only N news items

Cron: daily (new dividend declarations come in intermittently)
"""

import json
import os
import re
import sys
import time
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlparse

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    os.system(f"{sys.executable} -m pip install requests beautifulsoup4 lxml --quiet")
    import requests
    from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from db import get_db

MALAYSIA_TZ = timezone(timedelta(hours=8))
BASE_URL = "https://klse.i3investor.com"
NEWS_URL = f"{BASE_URL}/web/index"

# i3investor ticker stock quote page -> our stock code (e.g. "TMK" -> "TMK.KL")
# We'll try to match via the stocks table name or by looking up the code

def fetch_soup(url, retries=3):
    """Fetch a URL and return BeautifulSoup object."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "html.parser")
        except Exception as e:
            print(f"  ⚠ Fetch attempt {attempt+1}/{retries} failed: {e}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    return None


def extract_dividend_links(soup):
    """Extract dividend news links from the i3investor homepage.

    Looks for links under the 'News' section that mention 'Dividend'.
    """
    links = []
    seen_hrefs = set()

    # Find all news/detail links
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        text = a_tag.get_text(strip=True)

        # Match dividend-related news detail links
        if "/web/news/detail/" in href and ("dividend" in text.lower() or "dividen" in text.lower()):
            full_url = href if href.startswith("http") else f"{BASE_URL}{href}"
            if full_url not in seen_hrefs:
                seen_hrefs.add(full_url)
                links.append({"url": full_url, "title": text})

    return links


def parse_dividend_detail(soup, url):
    """Parse a dividend news detail page.

    Returns a dict with:
        ticker: stock ticker symbol (e.g. 'TMK')
        company_name: full company name from the title
        dividend: {announce_date, subject, amount, ex_date, payment_date}

    Returns None if parsing fails.
    """
    result = {"ticker": None, "company_name": None, "dividend": None, "url": url}

    # --- Extract title ---
    h3 = soup.find("h3")
    if h3:
        title_text = h3.get_text(strip=True)
        result["company_name"] = title_text

        # Parse company name: "TMK CHEMICAL BHD Announces Final Dividend of 2.8 Sen for 2026"
        # Take everything before "Announces" or "Declares"
        for keyword in [" Announces ", " Declares ", " announces ", " declares "]:
            if keyword in title_text:
                result["company_name"] = title_text.split(keyword)[0].strip()
                break

    # Try the "About X" heading for a more complete company name
    # e.g. "About SCIENTEX BERHAD" or "About TMK CHEMICAL BHD"
    about_section = soup.find(string=re.compile(r"About\s+"))
    if about_section:
        # Find the h5 heading containing "About"
        about_heading = about_section.find_parent(["h5", "h4", "h3", "h2"])
        if about_heading:
            about_link = about_heading.find("a")
            if about_link:
                about_company = about_link.get_text(strip=True)
                if about_company and len(about_company) > len(result["company_name"] or ""):
                    # Use the longer name as it's more complete
                    result["company_name"] = about_company

    # --- Extract ticker from Labels ---
    # Labels are shown as: Labels: TMK
    labels_div = soup.find(string=re.compile(r"Labels:", re.I))
    if labels_div:
        parent = labels_div.parent if labels_div.parent else labels_div
        label_links = parent.find_all("a") if parent else []
        # The label link is the ticker
        for link in label_links:
            ticker = link.get_text(strip=True)
            if ticker and len(ticker) <= 10 and ticker.isupper() and not ticker.startswith("http"):
                result["ticker"] = ticker
                break

    # If no label found, try the "Related Stocks" table
    if not result["ticker"]:
        # Find stock table cells with ticker-like text
        related_stock = soup.find(string=re.compile(r"Related Stocks"))
        if related_stock:
            table = related_stock.find_next("table")
            if table:
                for cell in table.find_all("td"):
                    link = cell.find("a")
                    if link:
                        ticker = link.get_text(strip=True)
                        if ticker and len(ticker) <= 10 and ticker.isupper() and not ticker.startswith("http"):
                            result["ticker"] = ticker
                            break

    # --- Extract dividend data table ---
    # Find the table with columns: Announce Date, Subject, Amount (RM), Ex-Date, Payment Date
    table = soup.find("table")
    rows = []
    if table:
        # Check if this is the dividend table by looking at headers
        headers = table.find_all("th")
        header_texts = [h.get_text(strip=True).lower() for h in headers]

        if any("announce date" in h or "subject" in h for h in header_texts):
            # This is the dividend table
            for tr in table.find_all("tr")[1:]:  # skip header row
                cells = tr.find_all("td")
                if len(cells) >= 5:
                    announce_date = cells[0].get_text(strip=True)
                    subject = cells[1].get_text(strip=True)
                    amount_str = cells[2].get_text(strip=True)
                    ex_date = cells[3].get_text(strip=True)
                    payment_date = cells[4].get_text(strip=True)

                    # Parse the last row (most recent dividend entry)
                    try:
                        amount = float(amount_str) if amount_str else 0.0
                    except ValueError:
                        amount = 0.0

                    rows.append({
                        "announceDate": announce_date,
                        "subject": subject,
                        "amount": amount,
                        "exDate": ex_date,
                        "paymentDate": payment_date,
                    })

    if rows:
        # Take the first (most recent/newly announced) row
        result["dividend"] = rows[0]
        result["all_dividends"] = rows  # include historical too for enrichment

    # --- Also extract publish date ---
    h6 = soup.find("h6")
    if h6:
        pub_text = h6.get_text(strip=True)
        m = re.search(r'(\d{4}-\d{2}-\d{2})', pub_text)
        if m:
            result["publish_date"] = m.group(1)

    return result


def get_stock_map():
    """Build a lookup dict: {ticker_name: stock_id, full_name: stock_id, code_only: stock_id}

    Returns dicts for flexible matching.
    """
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM stocks WHERE status NOT IN ('removed', 'data_missing')")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    name_to_id = {}
    ticker_to_id = {}
    code_to_id = {}

    for stock_id, stock_name in rows:
        # stock_id: "1155.KL" or "5250.KL"
        code_only = stock_id.replace(".KL", "").strip()

        # Store by code
        code_to_id[code_only] = stock_id
        code_to_id[code_only.lower()] = stock_id
        code_to_id[code_only.upper()] = stock_id

        # Store by full name (lowercased for matching)
        clean_name = stock_name.strip()
        name_to_id[clean_name.lower()] = stock_id

        # Also store first word of name (often the ticker)
        first_word = clean_name.split()[0].upper()
        ticker_to_id[first_word] = stock_id

        # Common tickers that are just the first part
        # e.g., "TMK" -> TMK CHEMICAL BHD
        short_code = code_only
        if not short_code.isalpha():  # numeric codes like "1155" are not tickers
            pass
        else:
            ticker_to_id[short_code] = stock_id

    return name_to_id, ticker_to_id, code_to_id


def match_stock(parsed, name_to_id, ticker_to_id, code_to_id):
    """Try to match a parsed dividend to a stock ID.

    Returns (stock_id, match_method) or (None, reason).
    """
    company = (parsed.get("company_name") or "").lower().strip()
    ticker = (parsed.get("ticker") or "").upper().strip()

    # 1. Try exact company name match
    if company in name_to_id:
        return name_to_id[company], "company_name"

    # 2. Try company name contains known stock name
    for stored_name, sid in name_to_id.items():
        # Check if parsed company is in stored name or vice versa
        if company and stored_name:
            company_words = set(company.split())
            stored_words = set(stored_name.split())
            # If significant overlap (e.g. "TMK Chemical Bhd" vs "TMK Chemical Berhad")
            overlap = company_words & stored_words
            # Only count meaningful words (not 'bhd', 'berhad', 'ltd', 'limited', 'sdn', 'sendirian', 'group', 'holdings')
            skip_words = {'bhd', 'berhad', 'ltd', 'limited', 'sdn', 'sendirian', 'group', 'holdings', '(m)', 'and', 'the', 'for', 'of', 'in', 'its'}
            meaningful = {w for w in overlap if w not in skip_words}
            if len(meaningful) >= 2:
                return sid, "fuzzy_name"
            # 2b. Single-word fallback: match only if the single word is distinctive
            # and appears as a prefix (e.g. "SCIENTEX" in "Scientex Berhad")
            # Avoid matching generic words like "industries", "development", "auto"
            generic_words = {'industries', 'industry', 'development', 'properties',
                             'property', 'capital', 'investment', 'auto', 'holdings',
                             'resources', 'engineering', 'technology', 'corporation',
                             'international', 'group', 'energy', 'healthcare'}
            if len(meaningful) == 1:
                only_word = list(meaningful)[0]
                if only_word in generic_words:
                    continue  # too generic to be a reliable match
                # Check if stored name starts with this word (case-insensitive)
                # AND the stored name's first word matches
                first_stored_word = stored_name.split()[0] if stored_name.split() else ''
                if first_stored_word == only_word:
                    return sid, "fuzzy_name_prefix"

    # 3. Try ticker match
    if ticker:
        if ticker in code_to_id:
            return code_to_id[ticker], "ticker_code"
        if ticker in ticker_to_id:
            return ticker_to_id[ticker], "ticker_name"

    return None, "no_match"


def write_dividends_to_db(stock_id, parsed_entry):
    """Append a dividend entry to stocks.dividends JSONB array.

    Deduplicates by (subject, announceDate) — won't insert the same
    declaration twice.
    """
    conn = get_db()
    cur = conn.cursor()

    try:
        # Get existing dividends
        cur.execute("SELECT dividends FROM stocks WHERE id = %s", (stock_id,))
        row = cur.fetchone()
        if not row:
            print(f"  ⚠ Stock {stock_id} not found")
            return False

        existing = row[0]
        if existing is None:
            existing = []
        elif isinstance(existing, str):
            existing = json.loads(existing)

        new_entry = {
            "announceDate": parsed_entry["announceDate"],
            "subject": parsed_entry["subject"],
            "amount": parsed_entry["amount"],
            "exDate": parsed_entry["exDate"],
            "paymentDate": parsed_entry["paymentDate"],
        }

        # Deduplicate by (subject, announceDate)
        for entry in existing:
            if isinstance(entry, dict):
                if (entry.get("subject") == new_entry["subject"]
                        and entry.get("announceDate") == new_entry["announceDate"]):
                    return False  # already exists

        # Append and update
        existing.append(new_entry)
        cur.execute(
            "UPDATE stocks SET dividends = %s, updated_at = now() WHERE id = %s",
            (json.dumps(existing), stock_id)
        )
        conn.commit()
        return True

    except Exception as e:
        conn.rollback()
        print(f"  ⚠ DB error: {e}")
        return False
    finally:
        cur.close()
        conn.close()


def main():
    news_only = "--news-only" in sys.argv
    max_news = None
    for arg in sys.argv:
        if arg.startswith("--max-news="):
            max_news = int(arg.split("=")[1])

    ts = datetime.now(MALAYSIA_TZ).isoformat()
    print(f"[{ts}] Starting dividend scraper...")

    # --- Step 1: Scrape news page for dividend links ---
    print(f"  Fetching {NEWS_URL}...")
    soup = fetch_soup(NEWS_URL)
    if not soup:
        print("  ✗ Failed to fetch homepage")
        return

    links = extract_dividend_links(soup)
    print(f"  Found {len(links)} dividend news links")

    if max_news and len(links) > max_news:
        links = links[:max_news]

    if not links:
        print("  No dividend news found")

    # --- Step 2: Build stock lookup ---
    if not news_only:
        name_to_id, ticker_to_id, code_to_id = get_stock_map()

    # --- Step 3: Parse each dividend news page ---
    success = 0
    skipped = 0
    errors = 0
    unmatched = []

    for i, link in enumerate(links):
        print(f"\n  [{i+1}/{len(links)}] {link['title'][:80]}...")
        print(f"    URL: {link['url']}")

        try:
            detail_soup = fetch_soup(link["url"])
            if not detail_soup:
                print(f"    ⚠ Failed to load detail page")
                errors += 1
                continue

            parsed = parse_dividend_detail(detail_soup, link["url"])
            if not parsed or not parsed.get("dividend"):
                print(f"    ⚠ Could not parse dividend data")
                errors += 1
                continue

            d = parsed["dividend"]
            print(f"    Ticker: {parsed.get('ticker', '?')}  "
                  f"Company: {parsed.get('company_name', '?')[:50]}")
            print(f"    {d['subject']} | Amount: RM {d['amount']} | "
                  f"Ex: {d['exDate']} | Pay: {d['paymentDate']}")

            if news_only:
                print(f"    [NEWS-ONLY mode, no DB write]")
                skipped += 1
                continue

            # Match to stock
            stock_id, method = match_stock(parsed, name_to_id, ticker_to_id, code_to_id)
            if not stock_id:
                print(f"    ⚠ Could not match stock — ticker={parsed.get('ticker')}, "
                      f"company={parsed.get('company_name')}")
                unmatched.append({
                    "title": link["title"],
                    "ticker": parsed.get("ticker"),
                    "company": parsed.get("company_name"),
                    "url": link["url"],
                })
                errors += 1
                continue

            print(f"    ✓ Matched to {stock_id} via {method}")

            # Write to DB
            if write_dividends_to_db(stock_id, d):
                print(f"    ✓ Dividend written to DB")
                success += 1
            else:
                print(f"    - Already exists (duplicate)")
                skipped += 1

            time.sleep(0.5)  # rate limit

        except Exception as e:
            print(f"    ✗ Error: {e}")
            traceback.print_exc()
            errors += 1

    # --- Summary ---
    ts_end = datetime.now(MALAYSIA_TZ).isoformat()
    print(f"\n[{ts_end}] Scrape complete!")
    print(f"  ✓ {success} new dividends written to DB")
    print(f"  – {skipped} skipped (duplicates/dry-run)")
    print(f"  ✗ {errors} errors")

    if unmatched:
        print(f"\n  ⚠ {len(unmatched)} unmatched stocks:")
        for u in unmatched:
            print(f"    - {u['title'][:80]}")
            print(f"      Ticker: {u['ticker']}, Company: {u['company']}")
            print(f"      {u['url']}")

    return success, skipped, errors, unmatched


if __name__ == "__main__":
    main()
