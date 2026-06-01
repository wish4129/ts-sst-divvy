-- RLS Migration: Enable Row Level Security on all Divvy tables
-- Run: npx drizzle-kit push (post-migration custom SQL)

-- ═══════════════════════════════════════════════════════
-- Enable RLS on all tables
-- ═══════════════════════════════════════════════════════
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE stocks ENABLE ROW LEVEL SECURITY;
ALTER TABLE stock_prices ENABLE ROW LEVEL SECURITY;
ALTER TABLE kronos_forecasts ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_portfolios ENABLE ROW LEVEL SECURITY;
ALTER TABLE portfolio_holdings ENABLE ROW LEVEL SECURITY;
ALTER TABLE trades ENABLE ROW LEVEL SECURITY;
ALTER TABLE portfolio_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_stock_picks ENABLE ROW LEVEL SECURITY;
ALTER TABLE screener_candidates ENABLE ROW LEVEL SECURITY;

-- ═══════════════════════════════════════════════════════
-- Public read tables (all authenticated users can read)
-- ═══════════════════════════════════════════════════════

-- stocks: readable by anyone authenticated
CREATE POLICY "stocks_read_all" ON stocks
  FOR SELECT TO authenticated USING (true);

-- stock_prices: readable by anyone authenticated
CREATE POLICY "stock_prices_read_all" ON stock_prices
  FOR SELECT TO authenticated USING (true);

-- kronos_forecasts: readable by anyone authenticated
CREATE POLICY "kronos_forecasts_read_all" ON kronos_forecasts
  FOR SELECT TO authenticated USING (true);

-- screener_candidates: readable by anyone authenticated
CREATE POLICY "screener_candidates_read_all" ON screener_candidates
  FOR SELECT TO authenticated USING (true);

-- ═══════════════════════════════════════════════════════
-- User-owned tables: user can CRUD their own rows
-- ═══════════════════════════════════════════════════════

-- users: read/update own profile
CREATE POLICY "users_read_own" ON users
  FOR SELECT TO authenticated
  USING (id = auth.uid());

CREATE POLICY "users_update_own" ON users
  FOR UPDATE TO authenticated
  USING (id = auth.uid());

-- user_portfolios: CRUD for the owner
CREATE POLICY "portfolios_select_own" ON user_portfolios
  FOR SELECT TO authenticated
  USING (user_id = auth.uid());

CREATE POLICY "portfolios_insert_own" ON user_portfolios
  FOR INSERT TO authenticated
  WITH CHECK (user_id = auth.uid());

CREATE POLICY "portfolios_update_own" ON user_portfolios
  FOR UPDATE TO authenticated
  USING (user_id = auth.uid());

CREATE POLICY "portfolios_delete_own" ON user_portfolios
  FOR DELETE TO authenticated
  USING (user_id = auth.uid());

-- portfolio_holdings: owner's portfolios only
CREATE POLICY "holdings_select_own" ON portfolio_holdings
  FOR SELECT TO authenticated
  USING (portfolio_id IN (
    SELECT id FROM user_portfolios WHERE user_id = auth.uid()
  ));

CREATE POLICY "holdings_insert_own" ON portfolio_holdings
  FOR INSERT TO authenticated
  WITH CHECK (portfolio_id IN (
    SELECT id FROM user_portfolios WHERE user_id = auth.uid()
  ));

CREATE POLICY "holdings_update_own" ON portfolio_holdings
  FOR UPDATE TO authenticated
  USING (portfolio_id IN (
    SELECT id FROM user_portfolios WHERE user_id = auth.uid()
  ));

CREATE POLICY "holdings_delete_own" ON portfolio_holdings
  FOR DELETE TO authenticated
  USING (portfolio_id IN (
    SELECT id FROM user_portfolios WHERE user_id = auth.uid()
  ));

-- trades: owner's portfolios only
CREATE POLICY "trades_select_own" ON trades
  FOR SELECT TO authenticated
  USING (portfolio_id IN (
    SELECT id FROM user_portfolios WHERE user_id = auth.uid()
  ));

CREATE POLICY "trades_insert_own" ON trades
  FOR INSERT TO authenticated
  WITH CHECK (portfolio_id IN (
    SELECT id FROM user_portfolios WHERE user_id = auth.uid()
  ));

-- portfolio_snapshots: owner's portfolios only
CREATE POLICY "snapshots_select_own" ON portfolio_snapshots
  FOR SELECT TO authenticated
  USING (portfolio_id IN (
    SELECT id FROM user_portfolios WHERE user_id = auth.uid()
  ));

CREATE POLICY "snapshots_insert_own" ON portfolio_snapshots
  FOR INSERT TO authenticated
  WITH CHECK (portfolio_id IN (
    SELECT id FROM user_portfolios WHERE user_id = auth.uid()
  ));

-- user_stock_picks: user can CRUD their own picks
CREATE POLICY "picks_select_own" ON user_stock_picks
  FOR SELECT TO authenticated
  USING (user_id = auth.uid());

CREATE POLICY "picks_insert_own" ON user_stock_picks
  FOR INSERT TO authenticated
  WITH CHECK (user_id = auth.uid());

CREATE POLICY "picks_update_own" ON user_stock_picks
  FOR UPDATE TO authenticated
  USING (user_id = auth.uid());

CREATE POLICY "picks_delete_own" ON user_stock_picks
  FOR DELETE TO authenticated
  USING (user_id = auth.uid());

-- ═══════════════════════════════════════════════════════
-- Service role bypass (for cron/scripts)
-- Supabase automatically bypasses RLS for service_role
-- No policy needed — service_role has full access
-- ═══════════════════════════════════════════════════════
