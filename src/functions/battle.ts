import { APIGatewayProxyHandlerV2 } from "aws-lambda";
import { drizzle } from "drizzle-orm/postgres-js";
import postgres from "postgres";
import * as schema from "../schema/schema";
import { userPortfolios, portfolioHoldings, stocks, portfolioSnapshots, trades } from "../schema/schema";
import { eq, desc } from "drizzle-orm";

// Connection pooler — explicit options (postgres-js URL parser splits username on '.')
const client = postgres({
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
    transform: { undefined: null },
});
const db = drizzle(client, { schema });

export const handler: APIGatewayProxyHandlerV2 = async () => {
  try {
    const portfolios = await db
      .select()
      .from(userPortfolios)
      .orderBy(userPortfolios.persona);

    const holdings = await db
      .select({
        portfolioId: portfolioHoldings.portfolioId,
        stockId: portfolioHoldings.stockId,
        shares: portfolioHoldings.shares,
        avgCost: portfolioHoldings.avgCost,
        targetPct: portfolioHoldings.targetPct,
        stockName: stocks.name,
      })
      .from(portfolioHoldings)
      .leftJoin(stocks, eq(portfolioHoldings.stockId, stocks.id));

    const latestSnapshots = await db
      .select()
      .from(portfolioSnapshots)
      .orderBy(desc(portfolioSnapshots.snapshotAt))
      .limit(50);

    const personaMap: Record<string, typeof portfolios[0]> = {};
    for (const pf of portfolios) {
      personaMap[pf.id] = pf;
    }

    const personaHoldings: Record<string, Record<string, any>> = {};
    for (const h of holdings) {
      const pid = h.portfolioId;
      if (!personaHoldings[pid]) personaHoldings[pid] = {};
      personaHoldings[pid][h.stockName || h.stockId] = {
        shares: h.shares,
        cost: Number(h.avgCost),
        price: Number(h.avgCost),  // default to cost (no live prices in API)
        invested: Math.round(h.shares * Number(h.avgCost) * 100) / 100,
        current: Math.round(h.shares * Number(h.avgCost) * 100) / 100,
        pnl: 0,
        pnl_pct: 0,
        weight: 0,
        targetPct: Number(h.targetPct),
      };
    }

    const snapByTime: Record<string, any> = {};
    for (const s of latestSnapshots) {
      const ts = s.snapshotAt?.toISOString() || "";
      if (!snapByTime[ts]) {
        snapByTime[ts] = { timestamp: ts, personas: {} };
      }
      const persona = personaMap[s.portfolioId]?.persona || "unknown";
      snapByTime[ts].personas[persona] = {
        total: Number(s.totalValue),
        invested: Number(s.invested),
        cash: Number(s.cash),
        pnl: Number(s.pnl),
        pnl_pct: Number(s.pnlPct),
        holdings: personaHoldings[s.portfolioId] || {},
        trades_this_run: 0,
      };
    }

    const runs = Object.values(snapByTime).sort(
      (a: any, b: any) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );

    const personaDefs: Record<string, any> = {};
    for (const pf of portfolios) {
      personaDefs[pf.persona] = {
        name: pf.name,
        cash: Number(pf.cash),
        holdings: personaHoldings[pf.id] || {},
      };
    }

    return {
      statusCode: 200,
      headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" },
      body: JSON.stringify({ runs, personas: personaDefs }),
    };
  } catch (error: any) {
    return {
      statusCode: 500,
      headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" },
      body: JSON.stringify({ error: error.message || "Internal error" }),
    };
  }
};
