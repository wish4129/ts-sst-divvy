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
        s.id as stock_id,
        s.name,
        s.industry,
        s.dividend_yield,
        s.dividends,
        GREATEST(s.score_composite, COALESCE(sa.score_composite, 0)) as composite_score,
        s.status
      FROM stocks s
      LEFT JOIN LATERAL (
        SELECT score_composite
        FROM stock_analyses
        WHERE stock_id = s.id
        ORDER BY generated_at DESC
        LIMIT 1
      ) sa ON true
      WHERE s.status != 'removed'
        AND s.dividends IS NOT NULL
        AND s.dividends != '[]'::jsonb
      ORDER BY s.dividend_yield DESC NULLS LAST
    `;

    const dividends = rows.map((r: any) => {
      const divList = typeof r.dividends === 'string' ? JSON.parse(r.dividends) : (r.dividends || []);
      // Find the upcoming/nearest ex-date
      const upcoming = divList
        .filter((d: any) => d.exDate)
        .sort((a: any, b: any) => a.exDate.localeCompare(b.exDate))[0];
      
      return {
        stockId: r.stock_id,
        name: r.name,
        industry: r.industry || '',
        dividendYield: Number(r.dividend_yield || 0),
        compositeScore: Number(r.composite_score || 0),
        status: r.status,
        dividends: divList.map((d: any) => ({
          announceDate: d.announceDate || null,
          subject: d.subject || '',
          amount: Number(d.amount || 0),
          exDate: d.exDate || null,
          paymentDate: d.paymentDate || null,
        })),
        nextExDate: upcoming?.exDate || null,
        nextAmount: upcoming ? Number(upcoming.amount || 0) : null,
      };
    });

    return {
      statusCode: 200,
      headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" },
      body: JSON.stringify(dividends),
    };
  } catch (error: any) {
    return {
      statusCode: 500,
      headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" },
      body: JSON.stringify({ error: error.message }),
    };
  }
};
