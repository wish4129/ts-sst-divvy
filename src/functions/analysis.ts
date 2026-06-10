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
  const persona = event.queryStringParameters?.persona;

  if (!code) {
    return { statusCode: 400, headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" },
             body: JSON.stringify({ error: "Missing stock code" }) };
  }

  try {
    if (persona) {
      const rows = await sql`
        SELECT sa.*, s.name as stock_name, s.industry, s.financials,
               s.last_price, s.price_change, s.market_cap, s.dividend_yield, s.sparkline
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
        body: JSON.stringify({
          persona: row.persona,
          stock_name: row.stock_name,
          industry: row.industry,
          score_composite: Number(row.score_composite),
          score_breakdown: row.score_breakdown,
          financials: row.financials,
          last_price: Number(row.last_price || 0),
          price_change: Number(row.price_change || 0),
          market_cap: Number(row.market_cap || 0),
          dividend_yield: Number(row.dividend_yield || 0),
          sparkline: row.sparkline || [],
          rationale: row.decision_rationale,
          kronos_signal: row.kronos_signal,
          macro_context: row.macro_context,
          ai_report: row.ai_report,
          ai_model: row.ai_model,
          generated_at: row.generated_at,
        }),
      };
    }

    // No persona — latest analysis + persona summary
    const latestRow = await sql`
      SELECT sa.*, s.name as stock_name, s.industry, s.financials,
             s.last_price, s.price_change, s.market_cap, s.dividend_yield, s.sparkline
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

    // Fallback: if no stock_analyses rows exist, return stocks table data directly
    if (!latest && personaRows.length === 0) {
      const stockRow = await sql`
        SELECT s.name, s.industry, s.financials,
               s.last_price, s.price_change, s.market_cap, s.dividend_yield, s.sparkline,
               s.score_composite, s.score_subs
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
          personas: {},
          ai_report: null,
          ai_model: null,
          score_composite: Number(s.score_composite || 0),
          score_breakdown: s.score_subs || null,
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
          persona: null,
        }),
      };
    }

    return {
      statusCode: 200,
      headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" },
      body: JSON.stringify({
        stock_name: latest?.stock_name || personaRows[0]?.stock_name || "",
        industry: latest?.industry || personaRows[0]?.industry || "",
        personas: byPersona,
        ai_report: latest?.ai_report || null,
        ai_model: latest?.ai_model || null,
        score_composite: latest ? Number(latest.score_composite) : 0,
        score_breakdown: latest?.score_breakdown || null,
        financials: latest?.financials || null,
        last_price: latest ? Number(latest.last_price || 0) : 0,
        price_change: latest ? Number(latest.price_change || 0) : 0,
        market_cap: latest ? Number(latest.market_cap || 0) : 0,
        dividend_yield: latest ? Number(latest.dividend_yield || 0) : 0,
        sparkline: latest?.sparkline || [],
        rationale: latest?.decision_rationale || null,
        kronos_signal: latest?.kronos_signal || null,
        macro_context: latest?.macro_context || null,
        generated_at: latest?.generated_at || null,
        persona: latest?.persona || null,
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
