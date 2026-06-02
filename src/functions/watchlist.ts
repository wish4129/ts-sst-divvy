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
        s.id as code,
        s.name,
        s.industry,
        s.initial_price as last_price,
        s.status,
        COALESCE(sa.score_composite, 0) as composite_score,
        CASE WHEN sa.ai_report IS NOT NULL THEN true ELSE false END as has_ai_report
      FROM stocks s
      LEFT JOIN LATERAL (
        SELECT score_composite, ai_report
        FROM stock_analyses
        WHERE stock_id = s.id
        ORDER BY generated_at DESC
        LIMIT 1
      ) sa ON true
      WHERE s.status != 'removed'
      ORDER BY COALESCE(sa.score_composite, 0) DESC
    `;

    const stocks = rows.map((r: any) => ({
      code: r.code,
      name: r.name,
      industry: r.industry || "",
      lastPrice: Number(r.last_price || 0),
      status: r.status,
      compositeScore: Number(r.composite_score || 0),
      hasAiReport: r.has_ai_report,
    }));

    return {
      statusCode: 200,
      headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" },
      body: JSON.stringify(stocks),
    };
  } catch (error: any) {
    return {
      statusCode: 500,
      headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" },
      body: JSON.stringify({ error: error.message }),
    };
  }
};
