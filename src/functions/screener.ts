import { APIGatewayProxyHandlerV2 } from "aws-lambda";
import postgres from "postgres";

const sql = postgres({
    host: "aws-1-ap-northeast-1.pooler.supabase.com",
    port: 6543,
    database: "postgres",
    username: "postgres.ceyqewaixcijbmdtbdlr",
    password: "pKj4k4JnoXAhRzrI",
    ssl: "require",
    max: 1, idle_timeout: 10, connect_timeout: 30, prepare: false,
});

export const handler: APIGatewayProxyHandlerV2 = async () => {
  try {
    const rows = await sql`
      SELECT
        sc.id,
        sc.stock_code,
        sc.stock_name,
        sc.pe_ratio,
        sc.dividend_yield,
        sc.roe,
        sc.composite_score,
        sc.scanned_at,
        CASE WHEN s.id IS NOT NULL THEN true ELSE false END as in_watchlist
      FROM screener_candidates sc
      LEFT JOIN stocks s ON s.id = sc.stock_code AND s.status != 'removed'
      ORDER BY sc.composite_score DESC NULLS LAST, sc.scanned_at DESC
    `;

    const candidates = rows.map((r: any) => ({
      id: r.id,
      stockCode: r.stock_code,
      stockName: r.stock_name,
      peRatio: r.pe_ratio ? Number(r.pe_ratio) : null,
      dividendYield: r.dividend_yield ? Number(r.dividend_yield) : null,
      roe: r.roe ? Number(r.roe) : null,
      compositeScore: r.composite_score || 0,
      scannedAt: r.scanned_at,
      inWatchlist: r.in_watchlist,
    }));

    return {
      statusCode: 200,
      headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" },
      body: JSON.stringify(candidates),
    };
  } catch (e: any) {
    return {
      statusCode: 500,
      headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" },
      body: JSON.stringify({ error: e.message }),
    };
  }
};
