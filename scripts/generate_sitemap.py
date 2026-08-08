"""Generate static web/public/sitemap.xml for Divvy.

This mirrors src/functions/sitemap.ts logic but outputs a static file
so CloudFront can serve it directly instead of returning SPA HTML.
"""

import sys
import os
import json
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape as xml_escape

# Ensure scripts/ is on path for db.py import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db import get_db, dict_cursor

OUTPUT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "web", "public", "sitemap.xml"
)

SITE_URL = os.environ.get("SITE_URL", "").rstrip("/")

# Never default to a hardcoded domain — the old CloudFront URL was deleted from
# AWS (see kanban t_22f077bc9ad2). If SITE_URL is unset, delete any stale
# sitemap rather than ship dead-domain URLs (SEO reset to zero). Set SITE_URL
# at deploy time: `SITE_URL=https://new-distro.cloudfront.net npx sst deploy`.
if not SITE_URL:
    print("⚠️  SITE_URL env var is not set — refusing to generate sitemap with dead/unknown domain.")
    stale = OUTPUT
    if os.path.exists(stale):
        os.remove(stale)
        print(f"⚠️  Removed stale {stale} to avoid serving dead-domain URLs. Set SITE_URL to regenerate.")
    print("ℹ️  Expected: SITE_URL=https://<new-distro>.cloudfront.net uv run python3 scripts/generate_sitemap.py")
    sys.exit(0)

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
]

# Blog post slugs — auto-discovered from web/src/content/blog/posts.json
BLOG_POSTS_JSON = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "web", "src", "content", "blog", "posts.json",
)

def get_blog_urls() -> list[dict]:
    """Read blog posts from posts.json and return sitemap entries."""
    try:
        with open(BLOG_POSTS_JSON) as f:
            posts = json.load(f)
        urls = []
        for post in posts:
            slug = post.get("slug", "")
            priority = "0.6" if slug == "coming-soon" else "0.8"
            changefreq = "monthly" if slug == "coming-soon" else "weekly"
            # Trailing slash required: generate_blog_meta.py emits
            # dist/blog/<slug>/index.html — S3 directory index serves
            # /blog/<slug>/ (mirrors the /stock/CODE/ pattern).
            urls.append({"loc": f"/blog/{slug}/", "priority": priority, "changefreq": changefreq})
        return urls
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"⚠️  Warning: could not read {BLOG_POSTS_JSON}: {e}")
        return []


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
    urls: list[str] = []

    for page in STATIC_PAGES:
        urls.append(make_url(page["loc"], page["priority"], page["changefreq"]))

    # Blog URLs — auto-discovered from posts.json
    for blog_page in get_blog_urls():
        urls.append(make_url(blog_page["loc"], blog_page["priority"], blog_page["changefreq"]))

    # Try to fetch stock URLs from DB; fall back to a static list of known stocks
    stock_lastmod: dict[str, str] = {}
    try:
        conn = get_db()
        cur = dict_cursor(conn)

        cur.execute("""
            SELECT id, name, updated_at
            FROM stocks
            WHERE status NOT IN ('removed', 'data_missing')
            ORDER BY score_composite DESC NULLS LAST
        """)
        stocks = cur.fetchall()

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

        for stock in stocks:
            lm = stock.get('updated_at')
            if lm is not None:
                # Normalize datetime/date → ISO date string (W3C datetime format)
                lm = lm.isoformat()[:10] if hasattr(lm, 'isoformat') else str(lm)[:10]
            stock_lastmod[stock['id']] = lm

        for s in universe:
            stock_lastmod[s['stock_code']] = None

        print(f"✅ DB connected: {len(stocks)} stocks, {len(universe)} universe entries")
    except Exception as e:
        print(f"⚠️  DB unavailable ({e}) — using static stock URL list")
        # FALLBACK (DEGRADED MODE): used ONLY when Supabase is unreachable at build.
        # WARNING: this covers 190 known codes vs ~805 in the DB — coverage is NOT
        # complete. lastmod = build date (the served static HTML does change at each
        # deploy). Restore DB access (see kanban t_4beaedcb7bb9) to regenerate the
        # full sitemap with per-stock updated_at lastmod. List = 165 prior codes +
        # 24 analyzed codes (stock_scores.json, Jun 4) + 0192.KL (INTA.KL migration target).
        import datetime
        fallback_lastmod = datetime.date.today().isoformat()
        fallback_codes = [
        "0052.KL","0099.KL","0104.KL","0138.KL","0166.KL","0192.KL","0206.KL",
        "0207.KL","0219.KL","0223.KL","0225.KL","0233.KL","0234.KL","0235.KL",
        "0243.KL","0245.KL","0251.KL","0253.KL","0255.KL","0257.KL","0261.KL",
        "0263.KL","0266.KL","0268.KL","0270.KL","0272.KL","0275.KL","0276.KL",
        "0280.KL","0281.KL","0282.KL","0283.KL","0284.KL","0285.KL","0286.KL",
        "0288.KL","0289.KL","0290.KL","0291.KL","0293.KL","0294.KL","0295.KL",
        "0296.KL","0297.KL","0298.KL","0299.KL","03001.KL","03003.KL","03005.KL",
        "03006.KL","03008.KL","03010.KL","03011.KL","03012.KL","03013.KL","03014.KL",
        "03015.KL","03016.KL","03017.KL","03018.KL","03019.KL","03020.KL","03021.KL",
        "03022.KL","03023.KL","03024.KL","03025.KL","03026.KL","03027.KL","03028.KL",
        "03029.KL","03030.KL","03031.KL","03032.KL","03033.KL","03034.KL","03035.KL",
        "03036.KL","03037.KL","03038.KL","03039.KL","03040.KL","03041.KL","03042.KL",
        "03043.KL","03044.KL","03045.KL","03046.KL","03047.KL","03048.KL","03049.KL",
        "03050.KL","03051.KL","03052.KL","03053.KL","03054.KL","03055.KL","03056.KL",
        "03057.KL","03058.KL","03059.KL","03060.KL","03061.KL","03062.KL","03063.KL",
        "03064.KL","1066.KL","1155.KL","1295.KL","1961.KL","2445.KL","3379.KL",
        "3816.KL","4065.KL","4197.KL","4677.KL","4715.KL","4731.KL","4863.KL",
        "5005.KL","5031.KL","5106.KL","5115.KL","5132.KL","5139.KL","5142.KL",
        "5236.KL","5250.KL","5264.KL","5279.KL","5280.KL","5288.KL","5293.KL",
        "5305.KL","5398.KL","5501.KL","5681.KL","5819.KL","5983.KL","6033.KL",
        "6383.KL","6399.KL","6599.KL","6742.KL","6819.KL","6947.KL","7052.KL",
        "7084.KL","7087.KL","7089.KL","7091.KL","7106.KL","7122.KL","7134.KL",
        "7200.KL","7204.KL","7205.KL","7206.KL","7208.KL","7212.KL","7227.KL",
        "7231.KL","7232.KL","7235.KL","7244.KL","7247.KL","7251.KL","7255.KL",
        "7257.KL","7260.KL","7261.KL","7263.KL","7271.KL","7273.KL","7275.KL",
        "7277.KL","7301.KL","7302.KL","9164.KL","9276.KL","9598.KL","9785.KL",
        "9796.KL","9844.KL","9859.KL","9887.KL","9938.KL","9939.KL","9946.KL",
        "9954.KL",
        ]
        for code in fallback_codes:
            stock_lastmod[code] = fallback_lastmod
        print(f"⚠️  Using {len(fallback_codes)} fallback stock codes for sitemap (lastmod={fallback_lastmod})")

    for code in sorted(stock_lastmod):
        # Trailing slash so CloudFront+S3 directory index serves the static HTML
        urls.append(make_url(f"/stock/{code}/", "0.8" if True else "0.6", "daily", lastmod=stock_lastmod.get(code)))

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
