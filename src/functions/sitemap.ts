import type { APIGatewayProxyEventV2, APIGatewayProxyResultV2 } from "aws-lambda";
import postgres from "postgres";

const sql = postgres({
  host: "aws-1-ap-northeast-1.pooler.supabase.com",
  port: 6543,
  database: "postgres",
  username: "postgres.ceyqewaixcijbmdtbdlr",
  password: "pKj4k4JnoXAhRzrI",
  ssl: "require",
  max: 1,
});

const SITE_URL = "https://d2d7b6u77b6we4.cloudfront.net";
const STATIC_PAGES = [
  { loc: "/", priority: "1.0", changefreq: "daily" },
  { loc: "/battle", priority: "0.9", changefreq: "daily" },
  { loc: "/watchlist", priority: "0.8", changefreq: "hourly" },
  { loc: "/universe", priority: "0.8", changefreq: "daily" },
  { loc: "/compare", priority: "0.7", changefreq: "weekly" },
  { loc: "/dividends", priority: "0.7", changefreq: "daily" },
  { loc: "/screener", priority: "0.7", changefreq: "weekly" },
  { loc: "/disclaimer", priority: "0.4", changefreq: "monthly" },
  { loc: "/privacy", priority: "0.4", changefreq: "monthly" },
  { loc: "/terms", priority: "0.4", changefreq: "monthly" },
];

function escapeXml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function urlXml(
  loc: string,
  priority: string,
  changefreq: string,
  lastmod?: string
): string {
  return `  <url>
    <loc>${escapeXml(SITE_URL + loc)}</loc>
    <priority>${priority}</priority>
    <changefreq>${changefreq}</changefreq>${lastmod ? `\n    <lastmod>${lastmod}</lastmod>` : ""}
  </url>`;
}

export async function handler(
  _event: APIGatewayProxyEventV2
): Promise<APIGatewayProxyResultV2> {
  try {
    // Fetch ALL non-removed stocks for full sitemap coverage
    const stocks: { id: string; name: string; updated_at: string }[] =
      await sql`
        SELECT id, name, updated_at
        FROM stocks
        WHERE status NOT IN ('removed', 'data_missing')
        ORDER BY score_composite DESC NULLS LAST
      `;

    // Fetch all analyzed universe stocks — exclude those already in stocks to avoid duplicates
    const universe: { stock_code: string; name: string }[] = await sql`
      SELECT stock_code, name
      FROM bursa_universe
      WHERE stock_code NOT IN (SELECT id FROM stocks WHERE status NOT IN ('removed', 'data_missing'))
      ORDER BY name ASC
    `;

    const urls: string[] = [];

    // Static pages
    for (const page of STATIC_PAGES) {
      urls.push(urlXml(page.loc, page.priority, page.changefreq));
    }

    // Active watchlist stock detail pages
    for (const stock of stocks) {
      const lastmod = stock.updated_at
        ? new Date(stock.updated_at).toISOString().slice(0, 10)
        : undefined;
      urls.push(
        urlXml(`/stock/${stock.id}`, "0.8", "daily", lastmod)
      );
    }

    // Universe pages (all stocks in the Bursa universe that have analysis)
    for (const s of universe) {
      urls.push(urlXml(`/stock/${s.stock_code}`, "0.6", "weekly"));
    }

    const sitemap = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls.join("\n")}
</urlset>`;

    return {
      statusCode: 200,
      headers: {
        "content-type": "application/xml",
        "cache-control": "public, max-age=3600, s-maxage=3600",
        "access-control-allow-origin": "*",
      },
      body: sitemap,
    };
  } catch (err: any) {
    console.error("Sitemap error:", err);
    return {
      statusCode: 500,
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ error: err.message }),
    };
  }
}
