import { APIGatewayProxyHandlerV2 } from "aws-lambda";
import postgres from "postgres";

const sql = postgres({
    host: "aws-1-ap-northeast-1.pooler.supabase.com",
    port: 6543,
    database: "postgres",
    username: "postgres.ceyqewaixcijbmdtbdlr",
    password: "pKj4k4JnoXAhRzrI",
    ssl: "require",
    max: 1,
    idle_timeout: 10,
    connect_timeout: 30,
    prepare: false,
});

export const handler: APIGatewayProxyHandlerV2 = async (event) => {
  const code = event.pathParameters?.code;
  const persona = event.queryStringParameters?.persona;

  if (!code) {
    return { statusCode: 400, headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" }, body: JSON.stringify({ error: "Missing stock code" }) };
  }

  try {
    if (persona) {
      // Return analysis for specific persona
      const rows = await sql`
        SELECT sa.*, s.name as stock_name, s.industry
        FROM stock_analyses sa
        JOIN stocks s ON sa.stock_id = s.id
        WHERE sa.stock_id = ${code} AND sa.persona = ${persona}
        ORDER BY sa.generated_at DESC LIMIT 1
      `;
      return {
        statusCode: 200,
        headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" },
        body: JSON.stringify(rows[0] || null),
      };
    }

    // Return all analyses for this stock (all personas)
    const rows = await sql`
      SELECT sa.*, s.name as stock_name, s.industry
      FROM stock_analyses sa
      JOIN stocks s ON sa.stock_id = s.id
      WHERE sa.stock_id = ${code}
      ORDER BY sa.persona
    `;

    const byPersona: Record<string, any> = {};
    for (const r of rows) {
      byPersona[r.persona] = r;
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
