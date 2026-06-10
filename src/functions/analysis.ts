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
      // Latest analysis for specific persona
      const rows = await sql`
        SELECT sa.*, s.name as stock_name, s.industry, s.financials
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
          rationale: row.decision_rationale,
          kronos_signal: row.kronos_signal,
          macro_context: row.macro_context,
          ai_report: row.ai_report,
          ai_model: row.ai_model,
          generated_at: row.generated_at,
        }),
      };
    }

    // No persona — return the latest analysis (any persona) with full AI report,
    // plus a summary of all personas
    const latestRow = await sql`
      SELECT sa.*, s.name as stock_name, s.industry, s.financials
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
        // Include latest AI report from any persona for watchlist view
        ai_report: latest?.ai_report || null,
        ai_model: latest?.ai_model || null,
        score_composite: latest ? Number(latest.score_composite) : 0,
        score_breakdown: latest?.score_breakdown || null,
        financials: latest?.financials || null,
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
