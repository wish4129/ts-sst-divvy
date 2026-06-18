# Divvy Changelog

All notable changes to the Divvy Bursa Malaysia investment platform.

---

## [Unreleased]

### 2026-06-18
- **Feat: search trajectory analytics** — logs anonymized search queries from Universe page to new `search_logs` table (migration 0004); new API endpoints `POST /universe/search-log` and `GET /analytics/top-searches`; tracking hook `useSearchAnalytics` (uncommitted — pending wire-up and deploy) [CANGJIE]
- **Feat: dividend calendar** — scraper, Lambda endpoint, and frontend page for upcoming ex-dates and yield tiers (9610cee8) [CANGJIE]
- **Chore: macro recalibration script** — weekly cron for >5% indicator moves, automates macro score refresh (26a36e09) [SAFE]
- **Fix: db health audit — simplify top 10 scores output** — remove AI report column, cleaner output (cd338503) [PANGU]
- **[MENSHEN] Remove static sitemap shadow, add blog routes to dynamic sitemap** — blog pages now indexed (b5301e75) [MENSHEN]
- **Fix: sync_from_db — escape newlines in notes field** — prevents SQL/JSON corruption on multi-line notes (5be8f5d0) [Internal]
- **Fix: TS types — make yield optional in DividendRecord** — add pivotTag, subject/paymentDate/announceDate fields for dividend calendar schema (5f26d232) [Internal]
- **Fix: Extract TS types to separate types.ts** — sync script imports shared types instead of redefining (3cb47d64, 99f54b55) [Internal]
- **[FUXI] Add explicit /battle route returning NotFound** — /battle was returning HTTP 200 with full app shell (SPA fallback), creating SEO soft-404 hygiene issue; now renders NotFound component via React Router (49e7bd42) [FUXI]
- **[MENSHEN] Add static sitemap generator** — scripts/generate_sitemap.py mirrors Lambda sitemap logic for stock + static + bursa_universe pages; outputs static sitemap.xml for CloudFront serving, fixing SPA intercept (bfb81604) [MENSHEN]

### 2026-06-16
- **[SHENNONG] Fix safe_float to reject Infinity values** — prevents ACE Market financial fetch crashes from division-by-zero floats (d461ca7c) [SHENNONG]
- **[PANGU] Add pivot_tag for sector-transitioning stocks** — flag stocks undergoing fundamental sector shifts (b86927af) [PANGU]
- **Feat: top 10 scored stocks in DB health audit** — adds a `db_health_audit.py` step that logs the 10 highest-scored stocks for quick health verification (24b92cb8) [PANGU]
- **KLSE Screener results updated** — committed latest screener data from Jun 15 run (0e5f84b6) [Internal]
- **Docs: strengthen disclaimer, remove tool references** — disclaimer now clearly states knowledge-sharing platform (no investment guidance); removed Kronos/yfinance tool references from legal pages and StockDetail (a8285b09, 20b9b372)
- **Fix: remove sitemap.xml and stocks.ts from .gitignore** — these should be tracked; restore from gitignore (3b0aa942)

### 2026-06-15
- **Blog system — pages, content, routing** — full blog infrastructure with Wenchang Bursa beginner guide; macro data updates + industry scorer enhancements (e03b6a19) [PANGU]

### 2026-06-14
- **Fix: StockDetail hooks ordering** — move `useMemo` before early returns to fix React hooks rule violation (#310) (c5d1d2e9) [PANGU]

### 2026-06-13
- **PANGU: ADR-002 Bursa ETF screener architecture** — architecture decision record for ETF screening feature (3862eb36) [PANGU]
- **PANGU: ADR-003 gearing risk verification** — ADR for gearing/leverage risk checks in stock analysis pipeline (3862eb36) [PANGU]

### 2026-06-12
- **[PANGU] Simplify scoring: drop 4-pillar display, keep only composite** — removed pillar breakdown UI in favor of single composite score (7bab8fe1) [PANGU]
- **Remove persona — drop Ares/Athena/Demeter portfolios** — removed DB tables, Battle page, strategies, and cron jobs associated with the persona system (347804fe)
- **Fix: remove persona_db dependency** — from run_random_analysis, financial_fetcher, and stock_analyses schema (556504db)
- **Fix(pangu): recreate persona_db.py** — fix ModuleNotFoundError after persona removal (d0abc522) [PANGU]
- **Suppress build/deploy output noise** — in run_random_analysis auto-deploy script (d0c66747) [Internal]

### 2026-06-11
- **Kronos forecasts refreshed** — 79 entries updated, refactored stocks.ts to API-driven (removed inline data) — 08fecd43 [Internal]
- **[FUXI] Fix sitemap duplicate URLs** — exclude universe stocks already in watchlist to prevent 76 duplicate stock pages; updated sitemap test mock order (2aa1d480) [FUXI]
- **Fix: fallback to random unanalyzed stocks when pending queue empty** — when no pending analyses are queued, pick a random unanalyzed stock instead of failing; keeps the analysis pipeline running at all times (57b3711d) [Internal]
- **Legal pages + sitemap** — Disclaimer, Privacy, Terms pages with sitemap.xml + robots.txt; data_missing stocks excluded from sitemap; footer Link import fix (58d797f7, 03438448, 89310a5b, bd14a98f)
- **[FUXI] Product + Organization JSON-LD** — structured data added to StockDetail pages for schema.org richness on stock profiles (046c1858) [FUXI]
- **data_missing stock status** — stocks with null PE/ROE excluded from analysis pipeline; priority queue re-fetches financials before analysis (61f7ee74, 459ef604)

### 2026-06-10
- **PANGU: test_industry_scorer** — update macro_adjustment calls to single-arg signature (3e07acb3) [PANGU]
- **CANGJIE: battle data + CHANGELOG update** — refreshed live_prices, portfolio_history for June 10 (288a5c0f) [Internal]
- **PANGU: test_sync_from_db.py** — 38 assertions covering null handling, TS output, ticker maps, edge cases (fef990d0) [PANGU]
- **Rebalance: pillar weights** — quality 35, dividend 25, growth 25, risk 15 (0925356f)
- **Refactor: uniform 4-pillar scoring** — for all industries, defer industry-specific factors (131f1fea)
- **Fix: Banking industry matrix** — use generic factors instead of unfetchable banking metrics (d8c6eebb)
- **Fix: yfinance DY is already percentage** — remove multiplication in financial_fetcher.py (19392ab7)
- **Fix: market cap formatting + DY data quality** — yfinance percentage bug (890bc6bf)
- **Fix: Home page MCap and DY** — read from API instead of hardcoded 0 (20ca28c3)
- **Fix: sitemap include all non-removed stocks** — remove dead /cron/status route (52498a9d)
- **Fix: remove /cron entirely** — not public-facing, use GSC instead (d0cc18ad)
- **Fix: remove Cron tab from public header nav** — not public-facing (3f98bb19)
- **Fix: TS errors** — PersonaAnalysis to PersonaDetail, restore TriggerItem interface (60fcf2a5)
- **Fix: yfinance D/E is percentage not ratio** — divide by 100, fallback to quarterly BS (53338d39)
- **Fix: Python 3.9 compat** — dict|None to Optional[dict] (43d330f1)
- **Fix: eliminate stock_analyses gaps** — scorer never skips, API fallback, random analysis writes analyses (6b66fde3)
- **Simplify: reset stock page** — single deep analysis, no personas, no triggers (1d8bfe89)
- **Feat: persona tabs on stock detail** (27bed782)
- **Feat: DB-driven AI report generator** — for all missing reports (5e6506f6)
- **Refactor: remove dead code and consolidate TICKER_TO_SHORT** (552146cc)
- **Portfolio battle 2026-06-10_1816** (3a48b404) [Internal]
- **Portfolio battle 2026-06-10_1532** (dd8430ef) [Internal]
- **Portfolio battle 2026-06-10_1502** (e458ac66) [Internal]
- **Portfolio battle 2026-06-10_1446** (81a206a0) [Internal]
- **Portfolio battle 2026-06-10_1416** (5eb46b85) [Internal]
- **Portfolio battle 2026-06-10_1403** (24c8ef36) [Internal]
- **Portfolio battle 2026-06-10_1346** (34e6908e) [Internal]
- **Portfolio battle snapshot** — June 10, 2026 13:32 (1160b010) [Internal]
- **Portfolio battle snapshot** — June 10, 2026 13:17 (5c0e03de) [Internal]
- **Fix: map score_breakdown factor names to categories, generate decision_rationale in scorer** (0a5050a4) [PANGU]
- **Portfolio battle snapshot** — June 10, 2026 13:05 (9ce7ba6f) [Internal]
- **Fix: inline stock columns in SQL** — postgres.js doesn't support template interpolation (4a0a2386) [PANGU]
- **Fix: return price/market/sparkline from analysis API, read in frontend** (1449a479) [PANGU]
- **Portfolio battle snapshot** — June 10, 2026 12:47 (86ff0016) [Internal]
- **Fix: add financials to no-persona API response** (1dbd146e) [PANGU]
- **Portfolio battle snapshot** — June 10, 2026 12:31 (92442f13) [Internal]
- **Portfolio battle snapshot** — June 10, 2026 12:16 (afdb679b) [Internal]
- **Portfolio battle snapshot** — June 10, 2026 12:01 (829a8686) [Internal]
- **Portfolio battle snapshot** — June 10, 2026 11:46 (ddf4192e) [Internal]
- **Portfolio battle snapshot** — June 10, 2026 11:31 (3b82a1fc) [Internal]
- **Portfolio battle snapshot** — June 10, 2026 11:16 (212a0478) [Internal]
- **Portfolio battle snapshot** — June 10, 2026 11:04 (1bf6cf1f) [Internal]
- **Portfolio battle snapshot** — June 10, 2026 10:46 (7f649633) [Internal]
- **Portfolio battle snapshot** — June 10, 2026 10:31 (7cd04756) [Internal]
- **Portfolio battle snapshot** — June 10, 2026 09:59 (1748c3b0) [Internal]
- **Fix robots.txt sitemap URL** — point to API Gateway (was CloudFront SPA) (036a7424) [FUXI]
- **Fix: DB-driven pipeline** — financial_fetcher→DB, industry_scorer reads DB, frontend reads score_breakdown (3cbe2b41) [PANGU]
- **Fix: pbRatio optional** in sync_from_db + type errors (224ea2c7, 0a4799ed) [PANGU]
- **Fix: remove ai_report IS NOT NULL filter** — breaks stocks without AI report (fe7acde6) [PANGU]
- **SEO integration — react-helmet-async + dynamic sitemap Lambda** — per-page meta tags via react-helmet-async, dynamic sitemap generation Lambda endpoint serving all stock pages (6638fd82) [FUXI]
- **Remove static sitemap.xml** — was overriding dynamic Lambda (only 5 URLs, missing 50+ stock pages) (f57fff4d) [FUXI]
- **Update robots.txt sitemap URL** — point to dynamic Lambda endpoint (b5e7888f)
- **Vitest tests for sitemap Lambda handler** — (b8751434) [PANGU]
- **Complete HEINEKEN TICKER_MAP** — across all 4 remaining scripts (d708ea0d) [PANGU]
- **Root-level npm test scripts** — add for vitest CWD sensitivity fix (8eb8de89) [PANGU] [Internal]
- **Untrack tsconfig.tsbuildinfo** — add to .gitignore (44c4e527) [PANGU] [Internal]
- **Sync generated data files** — HEINEKEN added, stock data updates (d08e7d37) [Internal]
- **Sync generated data files from DB** — date rollover to June 10 (e63df2f6) [Internal]
- **Add untracked scripts** — scrape_prices tests + targeted Kronos runner (4a721981) [Internal]
- **gen_missing_ai_reports.py** — universe stock AI report backfill script for non-portfolio scored stocks (5b6f64bb) [PANGU]
- **Centralize SEO meta tags** — `seo()` utility across all pages (737d59e6) [PANGU]
- **Cash drift health check script** — detects persona_config vs user_portfolios cash divergence > RM1 (b6d19adc) [PANGU]
- **Batch Kronos forecast runner** — perf improvement, refresh all 77 stocks (9a9f0087) [PANGU]
- **Portfolio battle snapshot** — June 10, 2026 09:19 (a71a1aa3) [Internal]

### 2026-06-09
- **pytest for run_deep_analysis.py** — 26 tests across parse_markdown_report, get_stocks_from_db, generate_ai_report, PERSONAS/SECTION_MAP validation (0c3fb073) [PANGU]
- **Auto sync persona_config cash after portfolio_manager cash update** — eliminates drift between user_portfolios.cash and persona_config.cash (6f37423c) [PANGU]
- **Consolidate TICKER_MAP** — add missing SEM+HEINEKEN to screener.py and backfill_stocks_from_ts.py; all 6 files now consistent (a576390d) [PANGU]
- **Random analysis: Bina Darulaman (6173.KL)** — score=37 revisit (f9ef0a7e)
- **Random analysis: SOLID AUTOMOTIVE (5242.KL)** — score=40 revisit + 53 Kronos forecasts (551be91d)
- **Add target_price and cut_loss_price columns to stocks table** — backfill active stocks with score>70 (3300560f)
- **Pending-analysis: +8079.KL (Lee Swee Kiat, score 59)** — added to pipeline with Kronos forecast regeneration (fcd7b9dc)

### 2026-06-08
- **Vitest isolation fix — add vi.unstubAllGlobals() cleanup** to prevent cross-file vitest pollution (ee65dcbb) [PANGU] [Internal]
- **Fleet-wide vitest isolation + pollution fixes** (a7d9dae9) [PANGU] [Internal]
- **Automated portfolio data updates** — chore commit updating portfolio data files (6a636ee0) [Internal]
- **Kronos forecast regeneration** — refreshed 44 forecasts from DB with np.float64 → float casting (2a21c460) [Internal]
- **Updated CONTEXT.md and kronos_forecast.json** — committed regenerated data files (dec86304) [Internal]
- **og-image.png for social sharing** — added missing 1200×630 OG image for link previews on WhatsApp/Telegram/Twitter (d7fdd805)
- **pytest for backtest metrics** — 39 tests: CAGR, Sharpe ratio, max drawdown, win rate, profit factor, Calmar ratio, Sortino ratio (363f613f) [Internal]
- **pytest for risk modules batch 2** — 93 tests: Kelly criterion edge cases, market regime detection, transaction cost modeling, sector exposure limits (bcab903b) [Internal]
- **pytest for risk modules batch 1** — 87 tests: backtesting, Monte Carlo, correlation, drawdown, sector limits, Kelly criterion, regime detection, transaction costs, performance attribution (d5cd4610) [Internal]
- **pytest for industry_scorer** — 21 tests: linear interpolation, macro adjustment, composite cap, fallback handler, data mapping (6a713d15) [Internal]
- **pytest for portfolio manager** — 17 tests: core buy/sell execution, trade logging, cash sync (076dd74a) [Internal]
- **Generated data files** — committed financials, portfolios, stocks.ts (4e639568) [Internal]

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

### Testing (603 tests, 39 files)
- **Vitest (web):** 189 tests, 23 files — pages (Watchlist, StockDetail, Home, Universe, Compare, DividendCalendar, Screener, AuthCallback, CronStatus), components (Header, StockCard, ScoreBadge, SparklineChart, IndustryFilter, ErrorBoundary, Loading, LoginGate, NotFound, ProgressBar, Toast), hooks (useApi, AuthContext, ToastContext), libraries (export-csv). Battle/persona tests removed with persona system.
- **Pytest (Python):** 414 tests, 16 files — market_data (15), persona_db ticker mapping (16), portfolio_history (78), risk modules batch 1 (87: backtesting, Monte Carlo, correlation, drawdown, sector limits, Kelly, regime, transaction costs, attribution), risk modules batch 2 (93: Kelly edge cases, market regime, transaction costs, sector exposure), backtest metrics (39: CAGR, Sharpe, max drawdown, win rate, profit factor, Calmar, Sortino), portfolio manager (17: core buy/sell execution), run_deep_analysis (26: parse_markdown_report, get_stocks_from_db, generate_ai_report, const validation), scrape_prices (43), strategies (78: ares trailing stop, RSI filter, volume confirmation)

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
