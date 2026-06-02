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
  } catch (err: any) {
    console.error("Universe handler error:", err);
    return { statusCode: 500, body: JSON.stringify({ error: err.message }) };
  }
}

async function listUniverse(event: APIGatewayProxyEventV2) {
  const q = event.queryStringParameters || {};
  const search = (q.search || "").trim().toLowerCase();
  const market = (q.market || "").trim();
  const page = Math.max(1, parseInt(q.page || "1"));
  const limit = Math.min(100, Math.max(5, parseInt(q.limit || "50")));
  const offset = (page - 1) * limit;

  // Build where clause using tagged template interpolation
  let countResult: any;
  let rows: any;

  if (search && market) {
    countResult = await sql`
      SELECT COUNT(*)::int as count FROM bursa_universe
      WHERE (LOWER(name) LIKE ${"%" + search + "%"} OR code LIKE ${"%" + search + "%"})
      AND market = ${market}
    `;
    rows = await sql`
      SELECT code, name, market, sector, in_watchlist as "inWatchlist", created_at as "createdAt"
      FROM bursa_universe
      WHERE (LOWER(name) LIKE ${"%" + search + "%"} OR code LIKE ${"%" + search + "%"})
      AND market = ${market}
      ORDER BY name ASC
      LIMIT ${limit} OFFSET ${offset}
    `;
  } else if (search) {
    countResult = await sql`
      SELECT COUNT(*)::int as count FROM bursa_universe
      WHERE (LOWER(name) LIKE ${"%" + search + "%"} OR code LIKE ${"%" + search + "%"})
    `;
    rows = await sql`
      SELECT code, name, market, sector, in_watchlist as "inWatchlist", created_at as "createdAt"
      FROM bursa_universe
      WHERE (LOWER(name) LIKE ${"%" + search + "%"} OR code LIKE ${"%" + search + "%"})
      ORDER BY name ASC
      LIMIT ${limit} OFFSET ${offset}
    `;
  } else if (market) {
    countResult = await sql`
      SELECT COUNT(*)::int as count FROM bursa_universe WHERE market = ${market}
    `;
    rows = await sql`
      SELECT code, name, market, sector, in_watchlist as "inWatchlist", created_at as "createdAt"
      FROM bursa_universe
      WHERE market = ${market}
      ORDER BY name ASC
      LIMIT ${limit} OFFSET ${offset}
    `;
  } else {
    countResult = await sql`SELECT COUNT(*)::int as count FROM bursa_universe`;
    rows = await sql`
      SELECT code, name, market, sector, in_watchlist as "inWatchlist", created_at as "createdAt"
      FROM bursa_universe
      ORDER BY name ASC
      LIMIT ${limit} OFFSET ${offset}
    `;
  }

  const total = (countResult as any)[0]?.count || 0;

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

  const ticker = `${code}.KL`;

  // Check if already in stocks
  const existing = await sql`SELECT id FROM stocks WHERE id = ${ticker}`;
  if ((existing as any[]).length > 0) {
    return {
      statusCode: 200,
      headers: { "content-type": "application/json", "access-control-allow-origin": "*" },
      body: JSON.stringify({ success: true, message: "Already in watchlist", stockId: ticker }),
    };
  }

  // Get company details from bursa_universe
  const company = await sql`SELECT name, market FROM bursa_universe WHERE code = ${code}`;
  if ((company as any[]).length === 0) {
    return { statusCode: 404, body: JSON.stringify({ error: "Company not found" }) };
  }

  const { name, market } = (company as any)[0];

  // Insert into stocks table
  await sql`
    INSERT INTO stocks (id, name, industry, initial_price, status)
    VALUES (${ticker}, ${name}, ${market}, 0, 'revisit')
    ON CONFLICT (id) DO NOTHING
  `;

  // Update in_watchlist flag
  await sql`UPDATE bursa_universe SET in_watchlist = true WHERE code = ${code}`;

  return {
    statusCode: 200,
    headers: { "content-type": "application/json", "access-control-allow-origin": "*" },
    body: JSON.stringify({ success: true, message: "Added to watchlist", stockId: ticker }),
  };
}
