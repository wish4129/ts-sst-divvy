"""Generate static web/public/sitemap.xml for Divvy.

This mirrors src/functions/sitemap.ts logic but outputs a static file
so CloudFront can serve it directly instead of returning SPA HTML.
"""

import sys
import os
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape as xml_escape

# Ensure scripts/ is on path for db.py import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db import get_db, dict_cursor

SITE_URL = "https://d2d7b6u77b6we4.cloudfront.net"
OUTPUT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "web", "public", "sitemap.xml"
)

STATIC_PAGES = [
    {"loc": "/", "priority": "1.0", "changefreq": "daily"},
    {"loc": "/watchlist", "priority": "0.8", "changefreq": "hourly"},
    {"loc": "/universe", "priority": "0.8", "changefreq": "daily"},
    {"loc": "/compare", "priority": "0.7", "changefreq": "weekly"},
    {"loc": "/dividends", "priority": "0.7", "changefreq": "daily"},
    {"loc": "/screener", "priority": "0.7", "changefreq": "weekly"},
    {"loc": "/disclaimer", "priority": "0.4", "changefreq": "monthly"},
    {"loc": "/privacy", "priority": "0.4", "changefreq": "monthly"},
    {"loc": "/terms", "priority": "0.4", "changefreq": "monthly"},
    {"loc": "/blog", "priority": "0.8", "changefreq": "weekly"},
    {"loc": "/blog/coming-soon", "priority": "0.6", "changefreq": "monthly"},
    {"loc": "/blog/how-to-invest-bursa-malaysia-beginners-guide", "priority": "0.8", "changefreq": "weekly"},
]


def make_url(loc: str, priority: str, changefreq: str, lastmod: str | None = None) -> str:
    url = f"  <url>\n"
    url += f"    <loc>{xml_escape(SITE_URL + loc)}</loc>\n"
    url += f"    <priority>{priority}</priority>\n"
    url += f"    <changefreq>{changefreq}</changefreq>\n"
    if lastmod:
        url += f"    <lastmod>{lastmod}</lastmod>\n"
    url += f"  </url>"
    return url


def main():
    conn = get_db()
    cur = dict_cursor(conn)

    # Active stocks (watchlist)
    cur.execute("""
        SELECT id, name, updated_at
        FROM stocks
        WHERE status NOT IN ('removed', 'data_missing')
        ORDER BY score_composite DESC NULLS LAST
    """)
    stocks = cur.fetchall()

    # Universe stocks not already in stocks
    cur.execute("""
        SELECT stock_code, name
        FROM bursa_universe
        WHERE stock_code NOT IN (
            SELECT id FROM stocks WHERE status NOT IN ('removed', 'data_missing')
        )
        ORDER BY name ASC
    """)
    universe = cur.fetchall()
    conn.close()

    urls: list[str] = []

    for page in STATIC_PAGES:
        urls.append(make_url(page["loc"], page["priority"], page["changefreq"]))

    for stock in stocks:
        lastmod = stock["updated_at"].strftime("%Y-%m-%d") if stock.get("updated_at") else None
        # Trailing slash so CloudFront+S3 directory index serves the static HTML
        urls.append(make_url(f"/stock/{stock['id']}/", "0.8", "daily", lastmod))

    for s in universe:
        # Trailing slash so CloudFront+S3 directory index serves the static HTML
        urls.append(make_url(f"/stock/{s['stock_code']}/", "0.6", "weekly"))

    sitemap_xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    sitemap_xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    sitemap_xml += "\n".join(urls)
    sitemap_xml += "\n</urlset>\n"

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(sitemap_xml)

    print(f"✅ Sitemap generated: {OUTPUT} ({len(urls)} URLs)")


if __name__ == "__main__":
    main()
