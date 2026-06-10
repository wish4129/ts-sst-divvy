# Divvy Changelog

All notable changes to the Divvy Bursa Malaysia investment platform.

---

## [Unreleased]

### 2026-06-10
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

### Testing (687 tests, 44 files)
- **Vitest (web):** 273 tests, 26 files — all pages (Battle, Watchlist, StockDetail, Home, Universe, Compare, DividendCalendar, Screener, AuthCallback, CronStatus), all components (Header, StockCard, ScoreBadge, SparklineChart, IndustryFilter, ErrorBoundary, Loading, LoginGate, NotFound, ProgressBar, Toast), hooks (useApi, AuthContext, ToastContext), libraries (strategies, export-csv)
- **Pytest (Python):** 414 tests, 18 files — market_data (15), persona_db ticker mapping (16), portfolio_history (78), risk modules batch 1 (87: backtesting, Monte Carlo, correlation, drawdown, sector limits, Kelly, regime, transaction costs, attribution), risk modules batch 2 (93: Kelly edge cases, market regime, transaction costs, sector exposure), backtest metrics (39: CAGR, Sharpe, max drawdown, win rate, profit factor, Calmar, Sortino), portfolio manager (17: core buy/sell execution), run_deep_analysis (26: parse_markdown_report, get_stocks_from_db, generate_ai_report, const validation)

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
