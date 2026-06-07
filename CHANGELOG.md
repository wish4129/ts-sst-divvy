# Divvy Changelog

All notable changes to the Divvy Bursa Malaysia investment platform.

---

## [Unreleased]

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

### Testing (253 tests, 25 files)
- All pages: Battle, Watchlist, StockDetail, Home, Universe, Compare, DividendCalendar, Screener, AuthCallback
- All components: Header, StockCard, ScoreBadge, SparklineChart, IndustryFilter, ErrorBoundary, Loading, LoginGate, NotFound, ProgressBar, Toast
- Hooks + Context: `useApi` (8), `AuthContext` (18), `ToastContext`
- Libraries: `strategies` (37), `export-csv` (4)

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
