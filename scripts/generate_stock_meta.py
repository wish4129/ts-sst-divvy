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


def main():
    dist_index = os.path.join(DIST_DIR, "index.html")
    if not os.path.exists(dist_index):
        print(f"❌ {dist_index} not found. Run vite build first.")
        sys.exit(1)

    index_html = open(dist_index, "r", encoding="utf-8").read()
    essential_tags = extract_essential_tags(index_html)

    try:
        conn = get_db()
        cur = dict_cursor(conn)
    except Exception as e:
        print(f"⚠️  DB unavailable ({e}) — skipping stock meta page generation")
        return

    # Get top 50 analyzed stocks
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
