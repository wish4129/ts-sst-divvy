import { sql } from 'drizzle-orm';
import {
  pgTable, uuid, text, numeric, integer, boolean, timestamp,
  date, serial, bigint, unique, index, jsonb,
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
  // Expanded columns (migration 0001)
  scoreComposite: integer('score_composite').default(50),
  scoreSubs: jsonb('score_subs').default(sql`'{}'`),
  financials: jsonb('financials').default(sql`'[]'`),
  dividends: jsonb('dividends').default(sql`'[]'`),
  lastPrice: numeric('last_price'),
  priceChange: numeric('price_change').default('0'),
  dividendYield: numeric('dividend_yield'),
  peRatio: numeric('pe_ratio'),
  roe: numeric('roe'),
  debtToEquity: numeric('debt_to_equity'),
  marketCap: numeric('market_cap'),
  sparkline: jsonb('sparkline').default(sql`'[]'`),
  notes: text('notes').default(''),
  revisitAt: timestamp('revisit_at', { withTimezone: true }),
  targetPrice: numeric('target_price'),
  cutLossPrice: numeric('cut_loss_price'),
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

// ── Kronos 30-day AI forecasts (weekly) ──
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

// ── Bursa Malaysia full stock universe (~1,000 listed companies) ──
export const bursaUniverse = pgTable('bursa_universe', {
  code: text('code').primaryKey(),              // stock code: '5250', '1155'
  name: text('name').notNull(),                 // full company name
  market: text('market').notNull(),             // 'Main Market', 'ACE Market', 'LEAP Market'
  sector: text('sector'),                       // sector classification (future enrichment)
  inWatchlist: boolean('in_watchlist').notNull().default(false),  // already in stocks table
  createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
});
