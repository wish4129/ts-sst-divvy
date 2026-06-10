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

const STOCK_COLS = `s.name as stock_name, s.industry, s.financials,
  s.last_price, s.price_change, s.market_cap, s.dividend_yield,
  s.sparkline`;

export const handler: APIGatewayProxyHandlerV2 = async (event) => {
  const code = event.pathParameters?.code;
  const persona = event.queryStringParameters?.persona;

  if (!code) {
    return { statusCode: 400, headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" },
             body: JSON.stringify({ error: "Missing stock code" }) };
  }

  try {
    if (persona) {
      // Latest analysis for specific persona
      const rows = await sql`
        SELECT sa.*, ${sql(STOCK_COLS)}
        FROM stock_analyses sa
        JOIN stocks s ON sa.stock_id = s.id
        WHERE sa.stock_id = ${code} AND sa.persona = ${persona}
        ORDER BY sa.generated_at DESC LIMIT 1
      `;
      const row = rows[0];
      if (!row) return { statusCode: 404, headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" }, body: JSON.stringify(null) };

      return {
        statusCode: 200,
        headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" },
        body: JSON.stringify(buildResponse(row, true)),
      };
    }

    // No persona — return the latest analysis (any persona),
    // plus a summary of all personas
    const latestRow = await sql`
      SELECT sa.*, ${sql(STOCK_COLS)}
      FROM stock_analyses sa
      JOIN stocks s ON sa.stock_id = s.id
      WHERE sa.stock_id = ${code}
      ORDER BY sa.generated_at DESC LIMIT 1
    `;

    const personaRows = await sql`
      SELECT DISTINCT ON (sa.persona) sa.persona, sa.score_composite, sa.generated_at,
             s.name as stock_name, s.industry
      FROM stock_analyses sa
      JOIN stocks s ON sa.stock_id = s.id
      WHERE sa.stock_id = ${code}
      ORDER BY sa.persona, sa.generated_at DESC
    `;

    const byPersona: Record<string, any> = {};
    for (const r of personaRows) {
      byPersona[r.persona] = {
        persona: r.persona,
        score_composite: Number(r.score_composite),
        generated_at: r.generated_at,
      };
    }

    const latest = latestRow[0];

    return {
      statusCode: 200,
      headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" },
      body: JSON.stringify({
        stock_name: latest?.stock_name || personaRows[0]?.stock_name || "",
        industry: latest?.industry || personaRows[0]?.industry || "",
        personas: byPersona,
        ai_report: latest?.ai_report || null,
        ai_model: latest?.ai_model || null,
        ...buildResponse(latest, false),
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

function buildResponse(row: any, includePersona: boolean) {
  const base = {
    score_composite: row ? Number(row.score_composite) : 0,
    score_breakdown: row?.score_breakdown || null,
    financials: row?.financials || null,
    last_price: row ? Number(row.last_price || 0) : 0,
    price_change: row ? Number(row.price_change || 0) : 0,
    market_cap: row ? Number(row.market_cap || 0) : 0,
    dividend_yield: row ? Number(row.dividend_yield || 0) : 0,
    sparkline: row?.sparkline || [],
    rationale: row?.decision_rationale || null,
    kronos_signal: row?.kronos_signal || null,
    macro_context: row?.macro_context || null,
    generated_at: row?.generated_at || null,
  };
  if (includePersona) {
    return { persona: row.persona, stock_name: row.stock_name, industry: row.industry, ...base };
  }
  return { ...base, persona: row?.persona || null };
}
