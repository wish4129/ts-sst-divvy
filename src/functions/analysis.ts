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
        SELECT sa.*, s.name as stock_name, s.industry
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
          rationale: row.decision_rationale,  // JSON object with 6 sections
          kronos_signal: row.kronos_signal,
          macro_context: row.macro_context,
          generated_at: row.generated_at,
          run_count: rows.length,
        }),
      };
    }

    // All personas for this stock — latest each
    const rows = await sql`
      SELECT DISTINCT ON (sa.persona) sa.*, s.name as stock_name, s.industry
      FROM stock_analyses sa
      JOIN stocks s ON sa.stock_id = s.id
      WHERE sa.stock_id = ${code}
      ORDER BY sa.persona, sa.generated_at DESC
    `;

    const byPersona: Record<string, any> = {};
    for (const r of rows) {
      byPersona[r.persona] = {
        persona: r.persona,
        score_composite: Number(r.score_composite),
        rationale: r.decision_rationale,
        kronos_signal: r.kronos_signal,
        generated_at: r.generated_at,
      };
    }

    return {
      statusCode: 200,
      headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" },
      body: JSON.stringify(byPersona),
    };
  } catch (error: any) {
    return {
      statusCode: 500,
      headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" },
      body: JSON.stringify({ error: error.message }),
    };
  }
};
