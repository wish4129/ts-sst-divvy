# Divvy — Bursa Malaysia Stock Analysis Platform

Divvy is a full-stack Bursa Malaysia stock analysis and screening platform. It combines automated financial data ingestion, multi-factor scoring (quality, dividend, growth, risk), Kronos ML forecasting, and a React frontend with watchlist management.

> **Disclaimer:** Divvy is a knowledge-sharing and research platform. Nothing on this site constitutes investment advice.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Hosting** | AWS via SST v3 (API Gateway + Lambda + CloudFront + S3) |
| **Frontend** | React + TypeScript + Vite + Recharts |
| **Database** | Supabase (PostgreSQL) with Drizzle ORM |
| **Python Backend** | Python 3.14 scripts (scheduled via cron) |
| **ML Forecasting** | Kronos-small (time-series forecast model) |
| **Testing** | Vitest (web) + Pytest (Python scripts) |

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
│   └── public/                 # Static assets, sitemap.xml
├── src/                        # SST Lambda functions
│   ├── functions/              # API handlers (analysis, watchlist, universe, sitemap, etc.)
│   └── schema/                 # Drizzle DB schema + migrations
├── scripts/                    # Python data pipeline
│   ├── backtest/               # Historical backtesting engine
│   ├── risk/                   # Risk modules (Kelly, correlation, regime detection, etc.)
│   ├── strategies/             # Strategy modules (trailing stop, RSI, volume)
│   ├── tests/                  # Pytest test files
│   ├── db.py                   # DB connection helper
│   ├── financial_fetcher.py    # yfinance data ingestion
│   ├── industry_scorer.py      # Multi-factor scoring pipeline
│   └── generate_sitemap.py     # Static sitemap generator
├── docs/                       # ADRs + plans
├── sst.config.ts               # SST v3 infrastructure config
└── CHANGELOG.md                # Project changelog
```

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
- **Risk Modules** — Kelly criterion, correlation matrix, market regime detection, sector limits
- **Blog System** — Wenchang Bursa beginner guides and market content
- **CSV Export** — Export watchlist data to CSV

## Build & Deploy

### Frontend Build Pipeline

The web app is built via Vite and deployed as an SST StaticSite to CloudFront:

```bash
npm run build        # tsc → vite build (web/)
npm run deploy       # sst deploy --stage live
```

### Python Pipeline

Python scripts run on the host (no container). Dependencies via `uv`:

```bash
# Run a specific pipeline step
uv run python3 scripts/financial_fetcher.py
uv run python3 scripts/industry_scorer.py
```

### Tests

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

### Sitemap Architecture

The sitemap uses a **static pre-build generation** approach for reliability and to avoid CloudFront SPA intercept issues:

1. **Static generator** (`scripts/generate_sitemap.py`) — runs at build time, queries the DB for all stock + static + bursa_universe pages (819+ URLs) and outputs `web/public/sitemap.xml`
2. **Git-tracked** — `web/public/sitemap.xml` is intentionally committed to git. This is a deliberate design choice: the static file is the single source of truth for search engines, and deployments always ship a known-good sitemap
3. **Dynamic Lambda sitemap endpoint is commented out** in `sst.config.ts` — replaced by the static approach to avoid the CloudFront SPA fallback intercepting `/sitemap.xml` requests
4. **`/battle` route** — returns HTTP 410 (Gone) via a CloudFront Function (`web/cloudfront-function.js`), preventing Google from indexing the now-removed persona battle page. Previously returned 200 with full app shell (soft-404)
5. **Coverage** — All stock detail pages, static pages (privacy, disclaimer, terms, about, blog), and bursa universe stock pages are included in the sitemap
6. **`robots.txt`** — points search engines to `https://divvy.my/sitemap.xml`

See `scripts/generate_sitemap.py` for the generator implementation.

## License

Private project — internal use only.
