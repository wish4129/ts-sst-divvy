import {
  pgTable, uuid, text, numeric, integer, boolean, timestamp,
  date, serial, bigint, unique, index,
} from 'drizzle-orm/pg-core';

// ── Users (Supabase auth.users + this profile) ──
export const users = pgTable('users', {
  id: uuid('id').defaultRandom().primaryKey(),
  name: text('name').notNull().default('Kevin Mun'),
  email: text('email'),
  defaultCapital: numeric('default_capital').notNull().default('10000'),
  notificationsEnabled: boolean('notifications_enabled').notNull().default(true),
  createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
});

// ── Global stock universe (cron-managed) ──
export const stocks = pgTable('stocks', {
  id: text('id').primaryKey(),                // stock code: '1155.KL'
  name: text('name').notNull(),
  industry: text('industry'),
  initialPrice: numeric('initial_price').notNull(),
  status: text('status').notNull().default('active'),
  kronosWarning: text('kronos_warning'),
  addedAt: timestamp('added_at', { withTimezone: true }).notNull().defaultNow(),
  updatedAt: timestamp('updated_at', { withTimezone: true }).notNull().defaultNow(),
});

// ── OHLCV history (yfinance, daily) ──
export const stockPrices = pgTable('stock_prices', {
  stockId: text('stock_id').notNull().references(() => stocks.id),
  date: date('date').notNull(),
  open: numeric('open').notNull(),
  high: numeric('high').notNull(),
  low: numeric('low').notNull(),
  close: numeric('close').notNull(),
  volume: bigint('volume', { mode: 'number' }).notNull().default(0),
}, (table) => [
  index('idx_prices_stock_date').on(table.stockId, table.date),
]);

// ── Kronos 30-day AI forecasts (weekly) ──
export const kronosForecasts = pgTable('kronos_forecasts', {
  id: serial('id').primaryKey(),
  stockId: text('stock_id').notNull().references(() => stocks.id),
  generatedAt: timestamp('generated_at', { withTimezone: true }).notNull().defaultNow(),
  pred30dClose: numeric('pred_30d_close').notNull(),
  predChangePct: numeric('pred_change_pct').notNull(),
  predLow: numeric('pred_low'),
  predHigh: numeric('pred_high'),
  predVolatility: numeric('pred_volatility'),
}, (table) => [
  index('idx_kronos_stock').on(table.stockId, table.generatedAt),
]);

// ── User portfolios (3 personas per user) ──
export const userPortfolios = pgTable('user_portfolios', {
  id: uuid('id').defaultRandom().primaryKey(),
  userId: uuid('user_id').notNull().references(() => users.id),
  persona: text('persona').notNull(),
  name: text('name').notNull(),
  strategy: text('strategy'),
  initialCapital: numeric('initial_capital').notNull().default('10000'),
  cash: numeric('cash').notNull().default('10000'),
  createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
  updatedAt: timestamp('updated_at', { withTimezone: true }).notNull().defaultNow(),
}, (table) => [
  unique('uq_user_portfolio').on(table.userId, table.persona),
]);

// ── Portfolio holdings (current positions) ──
export const portfolioHoldings = pgTable('portfolio_holdings', {
  portfolioId: uuid('portfolio_id').notNull().references(() => userPortfolios.id),
  stockId: text('stock_id').notNull().references(() => stocks.id),
  shares: integer('shares').notNull(),
  avgCost: numeric('avg_cost').notNull(),
  targetPct: numeric('target_pct').notNull(),
}, (table) => [
  unique('uq_holding').on(table.portfolioId, table.stockId),
]);

// ── Trades — full decision trail 🔑 ──
export const trades = pgTable('trades', {
  id: serial('id').primaryKey(),
  portfolioId: uuid('portfolio_id').notNull().references(() => userPortfolios.id),
  stockId: text('stock_id').notNull().references(() => stocks.id),
  action: text('action').notNull(),
  shares: integer('shares').notNull(),
  price: numeric('price').notNull(),
  totalAmount: numeric('total_amount').notNull(),
  reason: text('reason').notNull(),
  kronosSignal: text('kronos_signal'),
  decisionSource: text('decision_source'),
  triggeredBy: text('triggered_by'),
  snapshotId: integer('snapshot_id'),
  executedAt: timestamp('executed_at', { withTimezone: true }).notNull().defaultNow(),
}, (table) => [
  index('idx_trades_portfolio').on(table.portfolioId, table.executedAt),
  index('idx_trades_stock').on(table.stockId),
]);

// ── Portfolio snapshots (performance over time) ──
export const portfolioSnapshots = pgTable('portfolio_snapshots', {
  id: serial('id').primaryKey(),
  portfolioId: uuid('portfolio_id').notNull().references(() => userPortfolios.id),
  snapshotAt: timestamp('snapshot_at', { withTimezone: true }).notNull().defaultNow(),
  totalValue: numeric('total_value').notNull(),
  invested: numeric('invested').notNull(),
  cash: numeric('cash').notNull(),
  pnl: numeric('pnl').notNull(),
  pnlPct: numeric('pnl_pct').notNull(),
  holdingsJson: text('holdings_json'),
}, (table) => [
  index('idx_snapshots_portfolio').on(table.portfolioId, table.snapshotAt),
]);

// ── User stock picks (for "Divvy vs You" comparison) ──
export const userStockPicks = pgTable('user_stock_picks', {
  id: serial('id').primaryKey(),
  userId: uuid('user_id').notNull().references(() => users.id),
  stockId: text('stock_id').notNull().references(() => stocks.id),
  pickedAt: timestamp('picked_at', { withTimezone: true }).notNull().defaultNow(),
  pickedPrice: numeric('picked_price').notNull(),
  note: text('note'),
  active: boolean('active').notNull().default(true),
}, (table) => [
  unique('uq_user_stock_pick').on(table.userId, table.stockId),
]);

// ── Screener candidates (weekly discoveries) ──
export const screenerCandidates = pgTable('screener_candidates', {
  id: serial('id').primaryKey(),
  scannedAt: timestamp('scanned_at', { withTimezone: true }).notNull().defaultNow(),
  stockCode: text('stock_code').notNull(),
  stockName: text('stock_name').notNull(),
  peRatio: numeric('pe_ratio'),
  dividendYield: numeric('dividend_yield'),
  roe: numeric('roe'),
  compositeScore: integer('composite_score'),
  addedToUniverse: boolean('added_to_universe').notNull().default(false),
});
