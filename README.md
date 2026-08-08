# Divvy — Bursa Malaysia Stock Analysis Platform

Divvy is a full-stack Bursa Malaysia stock analysis and screening platform. It combines automated financial data ingestion, multi-factor industry scoring (15 industries × 6 factors), Kronos ML forecasting, and a React frontend with watchlist management.

> **Disclaimer:** Divvy is a knowledge-sharing and research platform. Nothing on this site constitutes investment advice.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Hosting** | AWS via SST v3 (API Gateway + Lambda + CloudFront + S3), region `ap-southeast-1` |
| **Frontend** | React + TypeScript + Vite + Recharts |
| **Database** | Supabase (PostgreSQL) with Drizzle ORM |
| **Python Backend** | Python 3.14 scripts (scheduled via Hermes cron agents) |
| **ML Forecasting** | Kronos-small (time-series forecast model) |
| **Testing** | Vitest (web) + Pytest (Python scripts) |

**Key architectural decisions:**
- **DB-first design** — all schema changes start in Drizzle ORM, migrations generated from source of truth
- **No static file commits** — data files like `stocks.ts` are regenerated nightly from the DB, not tracked in git
- **Supabase MCP tools** preferred for simple read-only DB operations; Python scripts share a single `scripts/db.py` connection helper for CRUD
- **Kanban board** (`~/.hermes/kanban/boards/divvy/kanban.db`) is the single source of truth for task tracking (386 done, 33 ready as of June 2026)

## Repo Structure

```
divvy/
├── web/                        # React frontend (Vite)
│   ├── src/
│   │   ├── pages/              # Home, Watchlist, Universe, StockDetail, Compare, etc.
│   │   ├── components/         # Shared UI: Header, StockCard, SparklineChart, Toast, etc.
│   │   ├── hooks/              # useApi, useSearchAnalytics
│   │   ├── contexts/           # AuthContext, ToastContext
│   │   ├── lib/                # API helpers
│   │   └── data/               # Stocks data + types
│   └── public/                 # Static assets, sitemap.xml, prerendered stock meta pages
├── src/                        # SST Lambda functions
│   ├── functions/              # API handlers (analysis, watchlist, universe, sitemap, etc.)
│   └── schema/                 # Drizzle DB schema + migrations
├── scripts/                    # Python data pipeline
│   ├── backtest/               # Historical backtesting engine
│   ├── risk/                   # Risk modules (Kelly, correlation, regime detection, sector limits, circuit breaker)
│   ├── strategies/             # Strategy modules (trailing stop, RSI filter, volume confirmation)
│   ├── tests/                  # Pytest test files
│   ├── db.py                   # Shared Supabase DB connection helper
│   ├── financial_fetcher.py    # yfinance data ingestion
│   ├── industry_scorer.py      # Multi-factor scoring pipeline (15 industries × 6 factors)
│   ├── generate_stock_meta.py  # Build-time prerender of per-stock SEO meta pages
│   └── generate_sitemap.py     # Static sitemap generator
├── docs/                       # ADRs + plans
├── sst.config.ts               # SST v3 infrastructure config
└── CHANGELOG.md                # Project changelog
```

## Scoring Pipeline Architecture

The industry scoring pipeline runs weekly and operates on 15 industry sectors × 6 scoring factors:

**Factors:** Quality, Dividend, Growth, Risk, Momentum, Value

**Sectors:** Banks, Consumer Cyclical, Consumer Defensive, Energy, Healthcare, Industrials, Basic Materials, Real Estate, Technology, Communication Services, Financial Services, Utilities, REITs, Closed-End Funds, Market

The pipeline:
1. **Financial fetcher** (`financial_fetcher.py`) — ingests yfinance data for all active stocks
2. **Industry scorer** (`industry_scorer.py`) — computes composite scores per industry with macro adjustments
3. **Deep analysis** (daily, Hermes cron) — LLM-powered analysis for active portfolio stocks
4. **Kronos forecasting** (daily, Hermes cron) — 30-day ML price forecasts with pre-check optimization

## Cron Job Roster

Divvy runs through Hermes cron. Key jobs:

| Name | Schedule | Description |
|------|----------|-------------|
| Divvy Morning Routine | Daily 8:30am MYT | Score, align, strategy adjust |
| Divvy Process Pending | Daily 10am MYT | Process pending stocks (daily pipeline step 0) |
| Divvy Deep Analysis | Daily 10:15am MYT | LLM analysis of active stocks (step 1) |
| Divvy Kronos Forecast | Daily 3am MYT | ML price forecast generation (step 2) |
| Divvy AI Reports | Daily 4am MYT | Reports generation (step 3) |
| Divvy KLSE Screener | Weekly Mon 9am | Automated Bursa candidate screening |
| Divvy Macro Score Re-Calibration | Weekly Mon 7am | Macro adjustment recalc |
| Divvy Dividend Scraper | Daily 1:30am | Ex-date and dividend data ingestion |
| Divvy New Listing Monitor | Daily 8am | Monitor Bursa for new IPO listings |
| Divvy DB Health Monitor | Once daily | Database integrity checks |
| Divvy Macro Fetch | Weekdays 8am | Economic indicator data ingestion |

All cron jobs use Hermes agent-mode (not shell scripts) for tasks requiring LLM analysis, and `no-agent` script mode for mechanical tasks like data fetching.

## Development Workflow

### DB-first approach

1. Modify Drizzle schema in `src/schema/`
2. Generate migrations: `npx drizzle-kit generate`
3. Apply: `npx drizzle-kit migrate`
4. The `db.py` Python helper auto-discovers the latest schema from Supabase

### Frontend Build Pipeline

```bash
npm run build        # tsc → vite build (web/)
npm run deploy       # sst deploy --stage live
```

The build also runs `generate_stock_meta.py` as a postbuild step to prerender static SEO meta pages for the top 50 analyzed stocks.

### Python Pipeline

Python scripts run on the host (no container). Dependencies via `uv`:

```bash
# Install Python deps (psycopg2-binary, boto3 - see requirements.txt)
uv pip install -r requirements.txt

# Run a specific pipeline step
uv run python3 scripts/financial_fetcher.py
uv run python3 scripts/industry_scorer.py

# Run all tests
uv run python3 -m pytest scripts/tests/
```

### Testing

```bash
# Web frontend
npm run test                   # vitest (web/)
npm run test:coverage          # with coverage report

# Python scripts
uv run python3 -m pytest scripts/tests/
```

## Infrastructure

- **AWS Region:** `ap-southeast-1` (Singapore)
- **Domain:** CloudFront distribution backed by S3 + API Gateway
- **Deploy:** `sst deploy --stage live` (IAM profile: `xion`)
- **Sitemap:** Static pre-build generation (`scripts/generate_sitemap.py`) — git-tracked, committed as single source of truth
- **Removed:** Persona portfolio simulation (Ares/Athena/Demeter) — all 6 DB tables, Battle page, Python scripts, and cron jobs deleted June 2026

## Key Features

- **Bursa Universe** — Browse all ~1,000 listed companies with search, filter, and search trajectory analytics
- **Watchlist** — Track active, revisit, pivot, and removed stocks with composite scores
- **Stock Detail** — Deep analysis with financials, score breakdown, Kronos forecasts, and AI reports
- **Stock Comparison** — Side-by-side metric comparison across stocks
- **Dividend Calendar** — Upcoming ex-dates with yield tiers, sortable table
- **Screener** — Automated Bursa candidate screening with deduplication
- **Sector Performance** — Multi-factor industry scoring with macro adjustments
- **Kronos Forecasting** — ML-based 30-day price forecasts for active stocks
- **Backtesting Engine** — Historical strategy replay with CAGR, Sharpe ratio, max drawdown
- **Risk Modules** — Kelly criterion, correlation matrix, market regime detection, sector exposure limits (50% cap), max drawdown circuit breaker
- **Strategy Modules** — Trailing stop-loss (ares.py), RSI-14 filter (rsi.py), 1.5x volume confirmation (volume.py)
- **Blog System** — Wenchang Bursa beginner guides and market content
- **CSV Export** — Export watchlist data to CSV
- **Search Analytics** — Trajectory tracking with click-through rate monitoring

## License

Private project — internal use only.
