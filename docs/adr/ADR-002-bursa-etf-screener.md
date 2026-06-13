# ADR-002: Bursa ETF Screener Tab

## Status
Accepted

## Context
Divvy's Universe page currently shows the full Bursa Malaysia stock universe (798 stocks). Bursa lists ~20 ETFs across equity, bond, gold, REIT, and leveraged/inverse categories that complement the stock screening experience. Demeter persona (dividend/REIT focused) would particularly benefit from ETF discovery alongside stocks.

The existing `bursa_universe` table holds all Bursa-listed instruments. ETFs need additional attributes (category, expense ratio, AUM) that don't apply to stocks. Adding these as nullable columns to `bursa_universe` avoids schema proliferation while keeping the data model simple.

## Options Considered

### Option A: Separate `etf_universe` table (rejected)
- Pros: Clean separation, different query patterns
- Cons: Duplicate infrastructure (import scripts, API endpoints, UI components), extra JOIN complexity if we ever want unified stock+ETF search

### Option B: Extended `bursa_universe` with ETF columns (chosen)
- Pros: Single data source, existing Universe API endpoint can be extended with `type` filter, simpler UI (tab pattern on existing page), easier yfinance validation pipeline
- Cons: Null columns for stocks (acceptable — many stock columns already nullable)

### Option C: No ETF support, focus on stock optimization
- Rejected. ETFs complement the Demeter persona and solve real user needs (dividend ETFs, REIT ETFs)

## Decision
**Extend `bursa_universe` with ETF-specific columns** and add an "ETFs" tab to the Universe page. This avoids schema overhead while enabling ETF discovery through the existing screening pipeline.

### Database Changes
Add to `bursa_universe`:
- `type` TEXT NOT NULL DEFAULT 'stock' CHECK(type IN ('stock', 'etf'))
- `etf_category` TEXT — 'Equity', 'Bond', 'Gold', 'REIT', 'Leveraged/Inverse', 'Money Market'
- `expense_ratio` NUMERIC — Annual management fee %
- `aum` NUMERIC — Assets under management (RM millions)
- `shariah` BOOLEAN DEFAULT NULL — Whether Shariah-compliant
- `return_1y` NUMERIC — 1-year return %
- `isin` TEXT — Unique identifier

### Frontend Changes
- Add "All | Stocks | ETFs" tab bar to Universe page header
- ETF tab shows additional columns: Category, Expense Ratio, AUM, Shariah, 1Y Return
- Filter chips for: category (dropdown), Shariah (toggle), min DY, max expense ratio
- Reuse existing download CSV export
- SEO: Separate meta description for ETF page

### Data Pipeline
1. Build Bursa ETF ticker list (~20 known ETFs from bursamalaysia.com)
2. Validate yfinance coverage for each (.KL tickers)
3. Create scripts/etf_fetcher.py — pulls yfinance ETF data (category, expense ratio, AUM, 1Y return)
4. Cron job: weekly ETF data refresh

## Consequences
- **Easier:** Existing Universe API (GET /universe) can be extended with `?type=etf` filter — minimal backend change
- **Easier:** Tab pattern follows existing UI conventions (no new page route needed)
- **Harder:** yfinance ETF data is less standardized than stock data — expense ratio and AUM may need manual curation for some tickers
- **Harder:** Initial data population requires manual ETF ticker compilation

## Decision Validation Points
- [ ] All ~20 Bursa ETFs identified and yfinance-validated
- [ ] bursa_universe migration adds columns without downtime
- [ ] Universe page renders ETF tab with correct filters
- [ ] Export CSV includes ETF-specific columns
