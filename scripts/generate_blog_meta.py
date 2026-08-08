"""Generate static HTML files for blog posts with per-post SEO meta tags.

Mirrors scripts/generate_stock_meta.py (the /stock/* prerender pattern).
Runs after 'vite build' to generate web/dist/blog/<slug>/index.html files
with post-specific title, meta description, canonical URL, and BlogPosting
JSON-LD structured data.

Before this script existed, /blog/<slug> URLs served the generic SPA shell
(2372 bytes): generic title "Divvy — Bursa Investment Tracker", canonical
pointing at the HOMEPAGE, no per-post description, no og:url, no JSON-LD.
Google saw every blog URL as a duplicate of the homepage (kanban t_366cb68e).

Slugs are read from web/src/content/blog/posts.json — the SAME source the
sitemap generator uses — so new posts are picked up automatically on build
and can never drift out of sync.

Usage: SITE_URL=https://<distro>.cloudfront.net .venv/bin/python3 scripts/generate_blog_meta.py
"""
import sys
import os
import json

SITE_URL = os.environ.get("SITE_URL", "").rstrip("/")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST_DIR = os.path.join(ROOT, "web", "dist")
BLOG_POSTS_JSON = os.path.join(ROOT, "web", "src", "content", "blog", "posts.json")

# Never default to a hardcoded domain — the old CloudFront URL was deleted from
# AWS (see kanban t_22f077bc9ad2). If SITE_URL is unset, skip generation rather
# than emit per-post pages whose canonical/og:image point at a dead domain.
if not SITE_URL:
    print("⚠️  SITE_URL env var is not set — skipping per-post blog meta page generation (canonicals would be dead-domain).")
    print("ℹ️  Expected: SITE_URL=https://<new-distro>.cloudfront.net .venv/bin/python3 scripts/generate_blog_meta.py")
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


def truncate(text, limit=155):
    """Truncate text to ~limit chars on a word boundary for meta descriptions."""
    text = str(text or "").strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut.rstrip(".,;:") + "…"


def generate_blog_page(index_html, essential_tags, post):
    """Generate a per-post HTML page with post-specific SEO meta."""
    slug = post["slug"]
    title = f"{post['title']} | Divvy"
    description = truncate(post.get("excerpt", ""))
    canonical = f"{SITE_URL}/blog/{slug}/"

    jsonld = json.dumps({
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": post["title"],
        "description": description,
        "url": canonical,
        "datePublished": post.get("date", ""),
        "author": {"@type": "Organization", "name": "Divvy"},
        "publisher": {
            "@type": "Organization",
            "name": "Divvy",
            "logo": {"@type": "ImageObject", "url": f"{SITE_URL}/og-image.png"},
        },
        "mainEntityOfPage": canonical,
    }, indent=2, default=str, ensure_ascii=False)

    head_content = f"""
    <title>{escape_html(title)}</title>
    <link rel="canonical" href="{escape_html(canonical)}" />
    <meta name="description" content="{escape_html(description)}" />
    <meta name="robots" content="index, follow" />
    <meta property="og:title" content="{escape_html(title)}" />
    <meta property="og:description" content="{escape_html(description)}" />
    <meta property="og:url" content="{escape_html(canonical)}" />
    <meta property="og:image" content="{SITE_URL}/og-image.png" />
    <meta property="og:type" content="article" />
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


def load_posts():
    """Read blog posts from posts.json (same source the sitemap uses)."""
    with open(BLOG_POSTS_JSON) as f:
        return json.load(f)


def main():
    dist_index = os.path.join(DIST_DIR, "index.html")
    if not os.path.exists(dist_index):
        print(f"❌ {dist_index} not found. Run vite build first.")
        sys.exit(1)

    try:
        posts = load_posts()
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"❌ Could not read {BLOG_POSTS_JSON}: {e}")
        sys.exit(1)

    index_html = open(dist_index, "r", encoding="utf-8").read()
    essential_tags = extract_essential_tags(index_html)

    print(f"📊 Generating static meta pages for {len(posts)} blog posts...")

    total = 0
    for post in posts:
        slug = post.get("slug", "")
        if not slug:
            print(f"  ⚠️  Skipping post without slug: {post.get('title', '?')}")
            continue
        page_html = generate_blog_page(index_html, essential_tags, post)

        page_dir = os.path.join(DIST_DIR, "blog", slug)
        os.makedirs(page_dir, exist_ok=True)
        page_path = os.path.join(page_dir, "index.html")
        with open(page_path, "w", encoding="utf-8") as f:
            f.write(page_html)

        total += 1
        print(f"  ✅ blog/{slug}/index.html — {post['title']}")

    print(f"✅ Done — {total} blog meta pages generated")


if __name__ == "__main__":
    main()
