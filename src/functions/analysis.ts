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

export const handler: APIGatewayProxyHandlerV2 = async (event) => {
  const code = event.pathParameters?.code;
  if (!code) {
    return { statusCode: 400, headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" },
             body: JSON.stringify({ error: "Missing stock code" }) };
  }

  try {
    // Latest analysis for this stock
    const latestRow = await sql`
      SELECT sa.*, s.name as stock_name, s.industry, s.financials,
             s.last_price, s.price_change, s.market_cap, s.dividend_yield, s.sparkline,
             s.pivot_tag
      FROM stock_analyses sa
      JOIN stocks s ON sa.stock_id = s.id
      WHERE sa.stock_id = ${code}
      ORDER BY sa.generated_at DESC LIMIT 1
    `;

    const latest = latestRow[0];

    // Fallback: if no analysis, return stocks table data
    if (!latest) {
      const stockRow = await sql`
        SELECT s.name, s.industry, s.financials,
               s.last_price, s.price_change, s.market_cap, s.dividend_yield, s.sparkline,
               s.score_composite, s.score_subs, s.pivot_tag
        FROM stocks s
        WHERE s.id = ${code}
      `;
      const s = stockRow[0];
      if (!s) return { statusCode: 404, headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" }, body: JSON.stringify(null) };

      return {
        statusCode: 200,
        headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" },
        body: JSON.stringify({
          stock_name: s.name,
          industry: s.industry || "",
          ai_report: null,
          ai_model: null,
          score_composite: Number(s.score_composite || 0),
          score_breakdown: s.score_subs || null,
          pivot_tag: s.pivot_tag || null,
          financials: s.financials || null,
          last_price: Number(s.last_price || 0),
          price_change: Number(s.price_change || 0),
          market_cap: Number(s.market_cap || 0),
          dividend_yield: Number(s.dividend_yield || 0),
          sparkline: s.sparkline || [],
          rationale: null,
          kronos_signal: null,
          macro_context: null,
          generated_at: null,
        }),
      };
    }

    return {
      statusCode: 200,
      headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" },
      body: JSON.stringify({
        stock_name: latest.stock_name || "",
        industry: latest.industry || "",
        ai_report: latest.ai_report || null,
        ai_model: latest.ai_model || null,
        score_composite: Number(latest.score_composite || 0),
        score_breakdown: latest.score_breakdown || null,
        pivot_tag: latest.pivot_tag || null,
        financials: latest.financials || null,
        last_price: Number(latest.last_price || 0),
        price_change: Number(latest.price_change || 0),
        market_cap: Number(latest.market_cap || 0),
        dividend_yield: Number(latest.dividend_yield || 0),
        sparkline: latest.sparkline || [],
        rationale: latest.decision_rationale || null,
        kronos_signal: latest.kronos_signal || null,
        macro_context: latest.macro_context || null,
        generated_at: latest.generated_at || null,
      }),
    };
  } catch (error: any) {
    return {
      statusCode: 500,
      headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" },
      body: JSON.stringify({ error: error.message }),
    };
  }
};
