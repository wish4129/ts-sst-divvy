import { APIGatewayProxyHandlerV2 } from "aws-lambda";
import { db } from "../db";
import { userPortfolios, portfolioHoldings, stocks, portfolioSnapshots, trades } from "../schema/schema";
import { eq, desc } from "drizzle-orm";

export const handler: APIGatewayProxyHandlerV2 = async () => {
  try {
    // Get all portfolios for user
    const portfolios = await db
      .select()
      .from(userPortfolios)
      .orderBy(userPortfolios.persona);

    // Get all holdings with stock names
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

    // Get latest snapshot per portfolio
    const latestSnapshots = await db
      .select()
      .from(portfolioSnapshots)
      .orderBy(desc(portfolioSnapshots.snapshotAt))
      .limit(50);

    // Get recent trades
    const recentTrades = await db
      .select({
        id: trades.id,
        portfolioId: trades.portfolioId,
        stockId: trades.stockId,
        action: trades.action,
        shares: trades.shares,
        price: trades.price,
        totalAmount: trades.totalAmount,
        reason: trades.reason,
        decisionSource: trades.decisionSource,
        executedAt: trades.executedAt,
      })
      .from(trades)
      .orderBy(desc(trades.executedAt))
      .limit(30);

    // Build response
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
        targetPct: Number(h.targetPct),
      };
    }

    // Snapshots grouped by timestamp
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

    // Convert to array sorted by time
    const runs = Object.values(snapByTime).sort(
      (a: any, b: any) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );

    // Persona definitions
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
      body: JSON.stringify({
        runs,
        personas: personaDefs,
        trades: recentTrades.map(t => ({
          id: t.id,
          portfolioId: t.portfolioId,
          stockId: t.stockId,
          action: t.action,
          shares: t.shares,
          price: Number(t.price),
          total: Number(t.totalAmount),
          reason: t.reason,
          source: t.decisionSource,
          time: t.executedAt?.toISOString(),
        })),
      }),
    };
  } catch (error: any) {
    return {
      statusCode: 500,
      headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" },
      body: JSON.stringify({ error: error.message || "Internal error" }),
    };
  }
};
