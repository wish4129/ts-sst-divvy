"""Generate static HTML files for top 50 analyzed stocks with per-stock SEO meta tags.

This is a postbuild script: runs after 'vite build' to generate
web/dist/stock/CODE/index.html files with stock-specific title, meta
description, canonical URL, and JSON-LD structured data.

Usage: python3 scripts/generate-stock-meta.py
"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db import get_db, dict_cursor

SITE_URL = os.environ.get("SITE_URL", "").rstrip("/")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST_DIR = os.path.join(ROOT, "web", "dist")

# Never default to a hardcoded domain — the old CloudFront URL was deleted from
# AWS (see kanban t_22f077bc9ad2). If SITE_URL is unset, skip generation rather
# than emit per-stock pages whose canonical/og:image point at a dead domain.
if not SITE_URL:
    print("⚠️  SITE_URL env var is not set — skipping per-stock meta page generation (canonicals would be dead-domain).")
    print("ℹ️  Expected: SITE_URL=https://<new-distro>.cloudfront.net .venv/bin/python3 scripts/generate_stock_meta.py")
    sys.exit(0)


def extract_essential_tags(html):
    """Extract essential non-SEO tags from the built index.html."""
    import re
    tags = []
    patterns = [
        r'<link rel="icon"[^>]*/?>',
        r'<link rel="manifest"[^>]*/?>',
        r'<link rel="apple-touch-icon"[^>]*/?>',
        r'<link rel="preconnect"[^>]*/?>',
        r'<link rel="dns-prefetch"[^>]*/?>',
        r'<meta name="viewport"[^>]*/?>',
        r'<meta name="theme-color"[^>]*/?>',
        r'<meta charset="[^"]*"?>',
        r'<link rel="modulepreload"[^>]*/?>',
        r'<link rel="stylesheet"[^>]*/?>',
        r'<script[^>]*src="[^"]*"[^>]*></script>',
    ]
    for pattern in patterns:
        for m in re.finditer(pattern, html, re.IGNORECASE):
            if m.group(0) not in tags:
                tags.append(m.group(0))
    return tags


def escape_html(text):
    """Escape HTML special characters."""
    return str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#039;')


def generate_stock_page(index_html, essential_tags, stock):
    """Generate a per-stock HTML page with stock-specific SEO meta."""
    title = f"{stock['name']} ({stock['code']}) — Stock Analysis | Divvy"
    description = f"View {stock['name']} ({stock['code']}) stock analysis on Divvy."
    if stock.get('industry'):
        description = f"View {stock['name']} ({stock['code']}) — {stock['industry']} stock analysis, composite score {stock.get('score_composite', 'N/A')}, and live KLSE price on Divvy."
    canonical = f"{SITE_URL}/stock/{stock['code']}/"

    score = stock.get('score_composite') or 0
    price = stock.get('last_price') or 0
    dy = stock.get('dividend_yield') or 0
    mcap = stock.get('market_cap') or 0

    jsonld = json.dumps({
        "@context": "https://schema.org",
        "@type": "FinancialProduct",
        "name": stock['name'],
        "identifier": stock['code'],
        "description": f"{stock['name']} ({stock['code']}) is a {stock.get('industry', 'Bursa Malaysia')} stock with composite score {score}.",
        "url": canonical,
        "offers": {
            "@type": "Offer",
            "price": float(price),
            "priceCurrency": "MYR",
        },
    }, indent=2, default=str)

    head_content = f"""
    <title>{escape_html(title)}</title>
    <link rel="canonical" href="{escape_html(canonical)}" />
    <meta name="description" content="{escape_html(description)}" />
    <meta name="robots" content="index, follow" />
    <meta property="og:title" content="{escape_html(title)}" />
    <meta property="og:description" content="{escape_html(description)}" />
    <meta property="og:url" content="{escape_html(canonical)}" />
    <meta property="og:image" content="{SITE_URL}/og-image.png" />
    <meta property="og:type" content="website" />
    <meta property="og:locale" content="en_MY" />
    <meta property="og:site_name" content="Divvy" />
    <meta name="twitter:card" content="summary_large_image" />
    <script type="application/ld+json">{jsonld}</script>
""".strip()

    new_head_content = '\n    '.join(['<meta charset="UTF-8" />', head_content] + essential_tags)

    import re
    result = re.sub(
        r'<head>[\s\S]*?</head>',
        '<head>\n    ' + new_head_content + '\n  </head>',
        index_html
    )

    return result


def load_fallback_stocks() -> list[dict]:
    """DB-independent stock data for per-stock meta pages (DEGRADED MODE).

    Used ONLY when Supabase is unreachable at build time. Sources (repo-local,
    committed): data/stock_scores.json (28 analyzed stocks with industry +
    composite score) and data/divvy.db.bak.2026-06-19 (17 stocks with industry).
    Deduplicated by code, stock_scores.json wins. Coverage is far below the
    top-50 DB query — this exists so the deploy NEVER ships zero per-stock meta
    pages (the silent no-op that shipped generic homepage meta for every stock
    page — see kanban t_4cc2b0a1 follow-up).
    """
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    by_code: dict[str, dict] = {}

    # Source 1: stock_scores.json (code, name, industry, composite)
    scores_path = os.path.join(root, "data", "stock_scores.json")
    try:
        with open(scores_path) as f:
            payload = json.load(f)
        for s in payload.get("scores", []):
            code = s.get("code")
            if not code:
                continue
            by_code[code] = {
                "code": code,
                "name": s.get("name", code),
                "industry": s.get("industry") or "",
                "score_composite": s.get("composite"),
                "last_price": 0,
                "dividend_yield": 0,
                "market_cap": 0,
            }
        print(f"ℹ️  Fallback source 1: {len(by_code)} stocks from data/stock_scores.json")
    except Exception as e:
        print(f"⚠️  Fallback source 1 unavailable ({e})")

    # Source 2: local sqlite backup (id, name, industry, status)
    backup_path = os.path.join(root, "data", "divvy.db.bak.2026-06-19")
    try:
        import sqlite3
        conn = sqlite3.connect(backup_path)
        rows = conn.execute(
            "SELECT id, name, industry, status FROM stocks"
        ).fetchall()
        conn.close()
        added = 0
        for row in rows:
            code, name, industry, status = row
            if status in ("removed", "data_missing") or code in by_code:
                continue
            by_code[code] = {
                "code": code,
                "name": name or code,
                "industry": industry or "",
                "score_composite": None,
                "last_price": 0,
                "dividend_yield": 0,
                "market_cap": 0,
            }
            added += 1
        print(f"ℹ️  Fallback source 2: +{added} stocks from data/divvy.db.bak.2026-06-19")
    except Exception as e:
        print(f"⚠️  Fallback source 2 unavailable ({e})")

    # Source 3: last-good committed stocks.ts (git HEAD) — ~150 stocks with
    # name/industry synced from the DB before it died. Working tree may be
    # truncated (sync_from_db writes 1 stock when DB is down), so read HEAD.
    try:
        import subprocess
        import re
        ts = subprocess.run(
            ["git", "show", "HEAD:web/src/data/stocks.ts"],
            capture_output=True, text=True, cwd=root, timeout=15,
        ).stdout
        # ticker map: '0043': '0043.KL'
        ticker_map = dict(re.findall(r"'([^']+)':\s*'([^']+\.KL)'", ts))
        # stock objects: code: 'XXXX', name: '...', industry: '...' (or null/'' )
        objs = re.findall(r"code:\s*'([^']+)'.*?name:\s*'([^']*)'.*?industry:\s*(?:'([^']*)'|null)", ts, re.S)
        added = 0
        for short, name, industry in objs:
            code = ticker_map.get(short, f"{short}.KL")
            if code in by_code:
                continue
            by_code[code] = {
                "code": code,
                "name": name or code,
                "industry": industry or "",
                "score_composite": None,
                "last_price": 0,
                "dividend_yield": 0,
                "market_cap": 0,
            }
            added += 1
        print(f"ℹ️  Fallback source 3: +{added} stocks from git HEAD web/src/data/stocks.ts")
    except Exception as e:
        print(f"⚠️  Fallback source 3 unavailable ({e})")

    return list(by_code.values())


def load_sitemap_stock_codes() -> list[str]:
    """Extract all /stock/* codes from web/public/sitemap.xml (generated by
    generate_sitemap.py BEFORE this script runs in the build pipeline).

    Every code listed in the sitemap MUST get a static HTML page: the SST
    StaticSite router sends /stock* paths to S3 directly (route prefix match)
    and returns raw S3 403 for missing keys — no SPA fallback. Any sitemap
    URL without a prerendered page is a guaranteed crawl error.
    """
    import re as _re
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sitemap_path = os.path.join(root, "web", "public", "sitemap.xml")
    codes: list[str] = []
    try:
        with open(sitemap_path) as f:
            content = f.read()
        codes = _re.findall(r"/stock/([^/<]+)/", content)
        print(f"ℹ️  Sitemap lists {len(codes)} stock URLs — all will get static pages")
    except FileNotFoundError:
        print(f"⚠️  {sitemap_path} not found — sitemap-coverage guarantee skipped")
    return codes


def main():
    dist_index = os.path.join(DIST_DIR, "index.html")
    if not os.path.exists(dist_index):
        print(f"❌ {dist_index} not found. Run vite build first.")
        sys.exit(1)

    index_html = open(dist_index, "r", encoding="utf-8").read()
    essential_tags = extract_essential_tags(index_html)

    degraded = False
    try:
        conn = get_db()
        cur = dict_cursor(conn)
    except Exception as e:
        degraded = True
        print(f"🚨 DEGRADED MODE: DB unavailable ({e}) — using repo-local fallback stock data")
        print(f"🚨 Per-stock meta coverage will be PARTIAL (~28-45 stocks, not top 50).")

    # Get top 50 analyzed stocks (DB mode)
    stocks = []
    if not degraded:
        cur.execute("""
            SELECT
                s.id as code,
                s.name,
                s.industry,
                s.score_composite,
                s.last_price,
                s.dividend_yield,
                s.market_cap,
                s.status
            FROM stocks s
            WHERE s.status NOT IN ('removed', 'data_missing')
            ORDER BY s.score_composite DESC NULLS LAST
            LIMIT 50
        """)
        stocks = cur.fetchall()
        conn.close()
    else:
        stocks = load_fallback_stocks()

    # Sitemap-coverage guarantee: every /stock/* URL in the sitemap gets a
    # static page (SST router 403s missing /stock* keys — no SPA fallback).
    # Rich entries keep their data; uncovered codes get a thin-but-valid page
    # with a correct per-stock canonical (never the homepage canonical).
    by_code = {s["code"]: s for s in stocks}
    for code in load_sitemap_stock_codes():
        if code not in by_code:
            by_code[code] = {
                "code": code,
                "name": code,
                "industry": "",
                "score_composite": None,
                "last_price": 0,
                "dividend_yield": 0,
                "market_cap": 0,
            }
    stocks = list(by_code.values())

    print(f"📊 Generating static meta pages for {len(stocks)} stocks...")

    total = 0
    for s in stocks:
        code = s['code']
        page_html = generate_stock_page(index_html, essential_tags, s)

        page_dir = os.path.join(DIST_DIR, "stock", code)
        os.makedirs(page_dir, exist_ok=True)
        page_path = os.path.join(page_dir, "index.html")
        with open(page_path, "w", encoding="utf-8") as f:
            f.write(page_html)

        total += 1
        if total <= 5 or total % 10 == 0:
            print(f"  ✅ stock/{code}/index.html — {s['name']}")

    print(f"✅ Done — {total} stock meta pages generated")


if __name__ == "__main__":
    main()
