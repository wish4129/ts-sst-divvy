# Implementation Plan: Bursa ETF Screener Tab

**Status:** Ready for development
**Priority:** Medium (enhancement)
**Tags:** PANGU, architecture, frontend, backend

## Summary
Add a searchable, filterable ETF screener tab to the Divvy Universe page. Users can browse ~20 Bursa ETFs alongside stocks, filtering by category, Shariah status, expense ratio, AUM, and yield.

## Phases

### Phase 1: ETF Ticker List + yfinance Validation
**Dependencies:** None
**Files involved:** `scripts/validate_etf_tickers.py` (created)
- Run `python3 scripts/validate_etf_tickers.py` to validate yfinance coverage
- Output: `data/etf_tickers.json` with validated tickers
- **Verify:** All ~20 ETF tickers return price data from yfinance
- **Fallback:** If yfinance is missing some, compile manual data from bursamalaysia.com

### Phase 2: DB Schema Migration
**Dependencies:** Phase 1
**Files involved:** `scripts/migrate_etf_schema.py` (created)
- Run `python3 scripts/migrate_etf_schema.py` to add ETF columns
- Adds: `asset_type`, `etf_category`, `expense_ratio`, `aum`, `shariah`, `return_1y`, `isin`
- **Verify:** `SELECT asset_type FROM bursa_universe LIMIT 1` works

### Phase 3: Data Ingest Script
**Dependencies:** Phase 1, Phase 2
**Files involved:** Create `scripts/etf_fetcher.py`
- Reads `data/etf_tickers.json`
- For each valid ETF, fetches yfinance data (expense ratio, AUM, yield, 1Y return)
- Populates `bursa_universe` rows with `asset_type='etf'`
- Updates weekly via cron (same schedule as financial_fetcher)

### Phase 4: Backend API Update
**Dependencies:** Phase 2
**Files involved:** `src/functions/*` (SST Lambda handlers)
- Update the Universe API endpoint to accept `?type=etf` query parameter
- Returns filtered results from `bursa_universe WHERE asset_type='etf'`
- For `type=stock`, preserve current behavior (WHERE asset_type='stock' OR asset_type IS NULL for backward compat)

### Phase 5: Frontend — Tab Bar + Filters
**Dependencies:** Phase 4
**Files involved:** `web/src/pages/Universe.tsx`
- Add "All | Stocks | ETFs" tab bar below the page title
- ETF tab shows custom columns:
  - Code · Name · Category · Expense Ratio · AUM · Shariah · 1Y Return
- Filter chips for ETFs:
  - Category dropdown: All, Equity, Bond, Gold, REIT, Leveraged/Inverse
  - Shariah toggle: All / Shariah / Non-Shariah
  - Min yield slider (0-10%)
  - Max expense ratio slider
- Reuse existing CSV export (add ETF-specific columns)

### Phase 6: SEO + Metadata
**Dependencies:** Phase 5
- Update Helmet SEO for ETF tab
- Add canonical URL for ETF view (e.g., `/etfs`)
- Update description to include ETF discovery

## File Map

| File | New/Modified | Purpose |
|------|-------------|---------|
| `scripts/validate_etf_tickers.py` | ✨ New | ETF ticker compilation + yfinance validation |
| `scripts/migrate_etf_schema.py` | ✨ New | DB schema migration for ETF columns |
| `scripts/etf_fetcher.py` | ✨ New | Weekly ETF data fetcher |
| `docs/adr/ADR-002-bursa-etf-screener.md` | ✨ New | Architecture Decision Record |
| `data/etf_tickers.json` | ✨ New | Validated ETF ticker list |
| `src/functions/<universe-handler>.ts` | ✏️ Modified | Add ?type=etf filter |
| `web/src/pages/Universe.tsx` | ✏️ Modified | Add ETF tab + filters |

## Effort Estimate
- **Phase 1:** 30 min (ticker list compilation + yfinance run)
- **Phase 2:** 15 min (migration script run + verify)
- **Phase 3:** 1h (data ingest script + cron config)
- **Phase 4:** 1h (backend API filter change)
- **Phase 5:** 2h (frontend tab UI + filter components)
- **Phase 6:** 15 min (SEO metadata)

**Total:** ~5h

## Blockers
- yfinance may not have expense_ratio / AUM for all ETFs — fallback to manual entries
- Some ETFs may be closed-ended funds (not true ETFs) — validate each
