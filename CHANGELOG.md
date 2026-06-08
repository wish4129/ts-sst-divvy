# Divvy Changelog

All notable changes to the Divvy Bursa Malaysia investment platform.

---

## [Unreleased]

### 2026-06-08
- **Kronos forecast regeneration** — refreshed 44 forecasts from DB with np.float64 → float casting (2a21c460) [Internal]
- **Updated CONTEXT.md and kronos_forecast.json** — committed regenerated data files (dec86304) [Internal]
- **og-image.png for social sharing** — added missing 1200×630 OG image for link previews on WhatsApp/Telegram/Twitter (d7fdd805)
- **pytest for backtest metrics** — 39 tests: CAGR, Sharpe ratio, max drawdown, win rate, profit factor, Calmar ratio, Sortino ratio (363f613f) [Internal]
- **pytest for risk modules batch 2** — 93 tests: Kelly criterion edge cases, market regime detection, transaction cost modeling, sector exposure limits (bcab903b) [Internal]
- **pytest for risk modules batch 1** — 87 tests: backtesting, Monte Carlo, correlation, drawdown, sector limits, Kelly criterion, regime detection, transaction costs, performance attribution (d5cd4610) [Internal]
- **pytest for industry_scorer** — 21 tests: linear interpolation, macro adjustment, composite cap, fallback handler, data mapping (6a713d15) [Internal]

### 2026-06-07
- **np.float64 → float() cast fix** — Kronos predictions now cast to native Python before psycopg2 INSERT; refreshed all 37 forecasts (262f0fa0)
- **Financial metrics on Compare page** — P/E, DY, ROE, D/E, Market Cap added via watchlist API (b6c86d44)
- **Pre-Monday Portfolio Risk Review** — YTL Power flagged for Ares SELL (Kronos -26.5%), SIME improved to -3.5%
- **Score Alert cron investigation** — root cause: transient Broken pipe to Supabase; script works, self-healed
- **pytest coverage** — 109 Python tests total: market_data (15) + persona_db ticker mapping (16) + history (78) (e97bedf9)
- **Fragment key warning** — React keys added to CronStatus job rows + test files excluded from tsc build
- **All 107 kanban tasks complete** — board fully done; 108/108 AI reports generated

### Phase 10 — Risk Management Engine
- **Backtesting engine** — historical replay of persona strategies with CAGR, Sharpe ratio, max drawdown metrics
- **Monte Carlo position sizing** — simulation-based optimal position sizing with confidence intervals
- **Correlation matrix** — concentration risk detection across portfolio holdings
- **Maximum drawdown circuit breaker** — persistent state, auto-halts trading at -20% drawdown
- **Sector exposure limits** — 50% cap per sector, enforced at rebalance
- **Kelly criterion** — risk-adjusted position sizing for optimal bet size
- **Market regime detection** — bull/bear/sideways classification for strategy switching
- **Transaction cost modeling** — brokerage (0.1%) + stamp duty (RM1/RM1000) baked into trade PnL
- **Performance attribution report** — factor-level PnL breakdown (momentum, dividend, sector, macro)

### Phase 6 — UI Polish
- **Dark mode toggle persistence** — localStorage + system preference detection in Header
- **NProgress-style loading bar** — animated progress bar during lazy route transitions
- **Toast notifications** — typed toasts (success/error/info/warning) with auto-dismiss and slide-in animation

### Phase 4 — Code Quality
- **Shared `useApi` hook** — replaces raw fetch patterns across all 5 pages
- **ErrorBoundary component** — graceful failure recovery with retry, 7 vitest tests
- **React.lazy + Suspense code splitting** — 12 JS chunks, per-page bundles

### Phase 5 — Responsive Design
- **Mobile-first layout** — responsive Battle, Watchlist, StockDetail pages

### Phase 8 — Performance
- **Bundle splitting** — recharts/supabase/vendor manual chunks (-56% main bundle)
- **Lighthouse CI** — automated audits on deploy (perf ≥ 90, a11y ≥ 95)
- **Preconnect hints** + image optimization

### Phase 6 — UX Animations
- **Page transition animations** — fadeInUp with reduced-motion respect
- **Micro-interactions** — card hover scale+shadow, row left-border highlight
- **Confetti celebration** — on PnL milestones (10%, 20%, etc.)

### Phase 7 — Accessibility (WCAG 2.1 AA)
- Skip-to-content link, ARIA labels, landmarks, keyboard navigation, form labels

### Phase 9 — SEO Foundation
- `robots.txt`, `sitemap.xml`, OG/Twitter meta tags, favicon, canonical URL

### Features
- **Dividend Calendar** — yield tiers, monthly view, sortable table
- **Stock Comparison** — side-by-side metric table, score breakdown bars, Kronos signals
- **CSV Export** — watchlist export with all columns
- **Screener Deduplication** — unique candidate tracking across runs
- **Strategy modules** — modular `ares.py` (trailing stop-loss), `rsi.py` (RSI-14 filter), `volume.py` (1.5x confirmation)

### Portfolio Engine
- **Portfolio Manager** now reads Kronos from DB directly (was file-only, fix for empty-file bug)
- **Live-priced holdings** in Battle API — reads `holdingsJson` from `portfolio_snapshots`
- **Sortable Battle holdings table** — shared sort state across all 3 persona tables
- **Portfolio allocation pie charts** — per-persona Recharts visualization

### Bug Fixes
- Deep Dive score circular read — uses `GREATEST(stocks.score, sa.max_score)`
- `useApi` refetch test race condition — wrapped `refetch()` in `act()`
- Missing `sql` import from drizzle-orm (500 on Battle API cold start)
- StockDetail early-return guards restored (removed by opencode)
- All scripts read from DB instead of stale files (`stocks.ts` no longer parsed)

### Testing (618 tests, 41 files)
- **Vitest (web):** 273 tests, 26 files — all pages (Battle, Watchlist, StockDetail, Home, Universe, Compare, DividendCalendar, Screener, AuthCallback, CronStatus), all components (Header, StockCard, ScoreBadge, SparklineChart, IndustryFilter, ErrorBoundary, Loading, LoginGate, NotFound, ProgressBar, Toast), hooks (useApi, AuthContext, ToastContext), libraries (strategies, export-csv)
- **Pytest (Python):** 345 tests, 15 files — market_data (15), persona_db ticker mapping (16), portfolio_history (78), risk modules batch 1 (87: backtesting, Monte Carlo, correlation, drawdown, sector limits, Kelly, regime, transaction costs, attribution), risk modules batch 2 (93: Kelly edge cases, market regime, transaction costs, sector exposure), backtest metrics (39: CAGR, Sharpe, max drawdown, win rate, profit factor, Calmar, Sortino), portfolio manager (17: core buy/sell execution)

### DB-First Pipeline (v4+)
- Stocks table JSONB columns expansion + Drizzle schema sync
- Backfill from stocks.ts into Supabase
- `sync_from_db.py` — DB → `stocks.ts` + `portfolios.json` (prebuild hook)
- DB-first insert helper (`insert_stock_db.py --sync`)
- All 6 Python scripts read from DB via `persona_db.py` helpers
- Bursa Universe — 798 stocks seeded, random deep analysis, pending queue

### Infrastructure
- Gitignore: `web/dist/`, `web/coverage/`, `.codegraph/`, `graphify-out/`
- SST deploy: missing notes handler stub, env var fixes
