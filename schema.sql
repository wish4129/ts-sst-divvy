-- Divvy Schema — SQLite (local) / Postgres (Supabase future)
-- Migration: same SQL runs on both. Only auth.users differs.
-- Run: sqlite3 data/divvy.db < schema.sql

-- ── Users (local: single user. Supabase: auth.users + this profile) ──
CREATE TABLE IF NOT EXISTS users (
    id          TEXT PRIMARY KEY DEFAULT 'kevin',  -- UUID in Supabase
    name        TEXT NOT NULL DEFAULT 'Kevin Mun',
    email       TEXT,
    default_capital NUMERIC NOT NULL DEFAULT 10000,
    notifications_enabled INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ── Global stock universe (cron-managed) ──
CREATE TABLE IF NOT EXISTS stocks (
    id          TEXT PRIMARY KEY,      -- stock code: '1155.KL'
    name        TEXT NOT NULL,
    industry    TEXT,
    initial_price NUMERIC NOT NULL,
    status      TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','bearish_flagged','removed')),
    kronos_warning TEXT,
    added_at    TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ── OHLCV history (yfinance, daily) ──
CREATE TABLE IF NOT EXISTS stock_prices (
    stock_id    TEXT NOT NULL REFERENCES stocks(id),
    date        TEXT NOT NULL,         -- 'YYYY-MM-DD'
    open        NUMERIC NOT NULL,
    high        NUMERIC NOT NULL,
    low         NUMERIC NOT NULL,
    close       NUMERIC NOT NULL,
    volume      BIGINT NOT NULL DEFAULT 0,
    PRIMARY KEY (stock_id, date)
);

-- ── Kronos 30-day AI forecasts (weekly) ──
CREATE TABLE IF NOT EXISTS kronos_forecasts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,  -- SERIAL in Postgres
    stock_id    TEXT NOT NULL REFERENCES stocks(id),
    generated_at TEXT NOT NULL DEFAULT (datetime('now')),
    pred_30d_close NUMERIC NOT NULL,
    pred_change_pct NUMERIC NOT NULL,
    pred_low    NUMERIC,
    pred_high   NUMERIC,
    pred_volatility NUMERIC
);

-- ── User portfolios (3 personas per user) ──
CREATE TABLE IF NOT EXISTS user_portfolios (
    id          TEXT PRIMARY KEY,      -- UUID
    user_id     TEXT NOT NULL REFERENCES users(id),
    persona     TEXT NOT NULL CHECK(persona IN ('ares','demeter','athena')),
    name        TEXT NOT NULL,
    strategy    TEXT,
    initial_capital NUMERIC NOT NULL DEFAULT 10000,
    cash        NUMERIC NOT NULL DEFAULT 10000,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, persona)
);

-- ── Portfolio holdings (current positions) ──
CREATE TABLE IF NOT EXISTS portfolio_holdings (
    portfolio_id TEXT NOT NULL REFERENCES user_portfolios(id),
    stock_id    TEXT NOT NULL REFERENCES stocks(id),
    shares      INTEGER NOT NULL,
    avg_cost    NUMERIC NOT NULL,
    target_pct  NUMERIC NOT NULL,
    PRIMARY KEY (portfolio_id, stock_id)
);

-- ── Trades — full decision trail 🔑 ──
CREATE TABLE IF NOT EXISTS trades (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id TEXT NOT NULL REFERENCES user_portfolios(id),
    stock_id    TEXT NOT NULL REFERENCES stocks(id),
    action      TEXT NOT NULL CHECK(action IN ('BUY','SELL','SELL_ALL')),
    shares      INTEGER NOT NULL,
    price       NUMERIC NOT NULL,
    total_amount NUMERIC NOT NULL,
    reason      TEXT NOT NULL,         -- "Kronos bearish -32.4% — proactive trim 15%"
    kronos_signal TEXT,                -- JSON: {"direction":"bearish","change_pct":-32.4,"strength":10}
    decision_source TEXT,              -- 'kronos_bearish_trim','stop_loss','rebalance','dip_buy',etc.
    triggered_by TEXT,                 -- Which persona rule fired
    snapshot_id INTEGER,               -- FK to portfolio_snapshots (for context)
    executed_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ── Portfolio snapshots (performance over time) ──
CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id TEXT NOT NULL REFERENCES user_portfolios(id),
    snapshot_at TEXT NOT NULL DEFAULT (datetime('now')),
    total_value NUMERIC NOT NULL,
    invested    NUMERIC NOT NULL,
    cash        NUMERIC NOT NULL,
    pnl         NUMERIC NOT NULL,
    pnl_pct     NUMERIC NOT NULL,
    holdings_json TEXT               -- Snapshot of holdings for historical comparison
);

-- ── User stock picks (for "Divvy vs You" comparison) ──
CREATE TABLE IF NOT EXISTS user_stock_picks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     TEXT NOT NULL REFERENCES users(id),
    stock_id    TEXT NOT NULL REFERENCES stocks(id),
    picked_at   TEXT NOT NULL DEFAULT (datetime('now')),
    picked_price NUMERIC NOT NULL,
    note        TEXT,
    active      INTEGER NOT NULL DEFAULT 1,
    UNIQUE(user_id, stock_id)
);

-- ── Screener candidates (weekly discoveries) ──
CREATE TABLE IF NOT EXISTS screener_candidates (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    scanned_at  TEXT NOT NULL DEFAULT (datetime('now')),
    stock_code  TEXT NOT NULL,
    stock_name  TEXT NOT NULL,
    pe_ratio    NUMERIC,
    dividend_yield NUMERIC,
    roe         NUMERIC,
    composite_score INTEGER,
    added_to_universe INTEGER NOT NULL DEFAULT 0
);

-- ── Indexes ──
CREATE INDEX IF NOT EXISTS idx_trades_portfolio ON trades(portfolio_id, executed_at);
CREATE INDEX IF NOT EXISTS idx_trades_stock ON trades(stock_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_portfolio ON portfolio_snapshots(portfolio_id, snapshot_at);
CREATE INDEX IF NOT EXISTS idx_prices_stock_date ON stock_prices(stock_id, date);
CREATE INDEX IF NOT EXISTS idx_kronos_stock ON kronos_forecasts(stock_id, generated_at);
