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

export async function handler(
  event: APIGatewayProxyEventV2
): Promise<APIGatewayProxyResultV2> {
  const method = event.requestContext.http.method;
  const path = event.rawPath;

  try {
    if (method === "GET" && path === "/universe") {
      return await listUniverse(event);
    }
    if (method === "POST" && path === "/universe/add") {
      return await addToWatchlist(event);
    }
    return { statusCode: 404, body: JSON.stringify({ error: "Not found" }) };
  } finally {
    // Don't close — reused across invocations
  }
}

async function listUniverse(event: APIGatewayProxyEventV2) {
  const q = event.queryStringParameters || {};
  const search = (q.search || "").trim();
  const market = (q.market || "").trim();
  const page = Math.max(1, parseInt(q.page || "1"));
  const limit = Math.min(100, Math.max(10, parseInt(q.limit || "50")));
  const offset = (page - 1) * limit;

  // Build query
  const conditions: string[] = [];
  const params: any[] = [];

  if (search) {
    conditions.push(`(LOWER(name) LIKE $${params.length + 1} OR code LIKE $${params.length + 2})`);
    params.push(`%${search.toLowerCase()}%`, `%${search}%`);
  }
  if (market) {
    conditions.push(`market = $${params.length + 1}`);
    params.push(market);
  }

  const where = conditions.length > 0 ? `WHERE ${conditions.join(" AND ")}` : "";

  // Count
  const countResult = await sql.unsafe(
    `SELECT COUNT(*) FROM bursa_universe ${where}`,
    ...params
  );
  const total = parseInt(String((countResult as any)[0]?.count || 0));

  // Fetch
  const rows = await sql.unsafe(
    `SELECT code, name, market, sector, in_watchlist as "inWatchlist", created_at as "createdAt"
     FROM bursa_universe ${where}
     ORDER BY name ASC
     LIMIT ${limit} OFFSET ${offset}`,
    ...params
  );

  return {
    statusCode: 200,
    headers: { "content-type": "application/json", "access-control-allow-origin": "*" },
    body: JSON.stringify({
      data: rows,
      pagination: { page, limit, total, totalPages: Math.ceil(total / limit) },
    }),
  };
}

async function addToWatchlist(event: APIGatewayProxyEventV2) {
  const body = JSON.parse(event.body || "{}");
  const { code } = body;

  if (!code) {
    return { statusCode: 400, body: JSON.stringify({ error: "code is required" }) };
  }

  // Check if already in stocks
  const ticker = `${code}.KL`;
  const existing = await sql.unsafe(
    `SELECT id FROM stocks WHERE id = $1`,
    ticker
  );

  if ((existing as any[]).length > 0) {
    return {
      statusCode: 200,
      headers: { "content-type": "application/json", "access-control-allow-origin": "*" },
      body: JSON.stringify({ success: true, message: "Already in watchlist", stockId: ticker }),
    };
  }

  // Get company details from bursa_universe
  const company = await sql.unsafe(
    `SELECT name, market FROM bursa_universe WHERE code = $1`,
    code
  );

  if ((company as any[]).length === 0) {
    return { statusCode: 404, body: JSON.stringify({ error: "Company not found" }) };
  }

  const { name, market } = (company as any)[0];

  // Insert into stocks table (use 0 as initial price — will be updated later)
  await sql.unsafe(
    `INSERT INTO stocks (id, name, industry, initial_price, status)
     VALUES ($1, $2, $3, 0, 'revisit')
     ON CONFLICT (id) DO NOTHING`,
    ticker, name, market
  );

  // Update in_watchlist flag
  await sql.unsafe(
    `UPDATE bursa_universe SET in_watchlist = true WHERE code = $1`,
    code
  );

  return {
    statusCode: 200,
    headers: { "content-type": "application/json", "access-control-allow-origin": "*" },
    body: JSON.stringify({ success: true, message: "Added to watchlist", stockId: ticker }),
  };
}
