# DB-First Pipeline Refactor Plan

> **For Hermes:** Implement with opencode using deepseek-v4-pro.

**Goal:** Make Supabase `stocks` table the single source of truth. All inserts and updates go to DB first. `stocks.ts` and `portfolios.json` are generated FROM the DB.

**Architecture:** Expand the `stocks` table to hold all stock data (scores, financials, dividends, sparklines) as JSONB columns. Add a sync script that reads DB → generates `stocks.ts` and `portfolios.json`. Build pipeline runs sync before `vite build`.

**Tech Stack:** Supabase Postgres, Python (psycopg2), Node.js (code generation)

---

## Problem

Current flow is error-prone:
```
Manual → stocks.ts + portfolios.json → (sometimes) DB
```

The 3-stock analysis today (PBBANK, TIME, SCICOM) got added to code files but DB was missed. DB should be the authority.

## Target Flow

```
Insert → Supabase DB → sync_from_db.py → stocks.ts + portfolios.json → vite build → deploy
```

---

### Task 1: Expand `stocks` table with JSONB columns

**Objective:** Add columns to hold all data currently in stocks.ts

**Files:**
- Create: `scripts/migrations/0001_expand_stocks.sql`

```sql
ALTER TABLE stocks ADD COLUMN IF NOT EXISTS score_composite INTEGER DEFAULT 50;
ALTER TABLE stocks ADD COLUMN IF NOT EXISTS score_subs JSONB DEFAULT '{}';
ALTER TABLE stocks ADD COLUMN IF NOT EXISTS financials JSONB DEFAULT '[]';
ALTER TABLE stocks ADD COLUMN IF NOT EXISTS dividends JSONB DEFAULT '[]';
ALTER TABLE stocks ADD COLUMN IF NOT EXISTS last_price NUMERIC;
ALTER TABLE stocks ADD COLUMN IF NOT EXISTS price_change NUMERIC DEFAULT 0;
ALTER TABLE stocks ADD COLUMN IF NOT EXISTS dividend_yield NUMERIC;
ALTER TABLE stocks ADD COLUMN IF NOT EXISTS pe_ratio NUMERIC;
ALTER TABLE stocks ADD COLUMN IF NOT EXISTS roe NUMERIC;
ALTER TABLE stocks ADD COLUMN IF NOT EXISTS debt_to_equity NUMERIC;
ALTER TABLE stocks ADD COLUMN IF NOT EXISTS market_cap NUMERIC;
ALTER TABLE stocks ADD COLUMN IF NOT EXISTS sparkline JSONB DEFAULT '[]';
ALTER TABLE stocks ADD COLUMN IF NOT EXISTS notes TEXT DEFAULT '';
ALTER TABLE stocks ADD COLUMN IF NOT EXISTS revisit_at TIMESTAMPTZ;
```

**Verify:** Run against Supabase via `scripts/db.py` connection.

---

### Task 2: Backfill existing stocks.ts data into DB

**Objective:** Migrate all 23 stocks from stocks.ts into the expanded DB table

**Files:**
- Create: `scripts/backfill_stocks_from_ts.py`

This script:
1. Parses `web/src/data/stocks.ts` (reuse existing parser from `run_deep_analysis.py`)
2. For each stock, UPSERT into DB with all fields
3. Reports count

**Run:** `python3 scripts/backfill_stocks_from_ts.py`

---

### Task 3: Create sync script (DB → code files)

**Objective:** Read DB, generate stocks.ts and portfolios.json

**Files:**
- Create: `scripts/sync_from_db.py`

Logic:
1. Query all stocks WHERE status != 'removed'
2. Generate TypeScript array output matching the `Stock[]` interface
3. Write to `web/src/data/stocks.ts` (preserving the `export const stocks` wrapper + INDUSTRY_COLORS)
4. Generate `portfolios.json` — only the `stocks` registry section (persona holdings stay manual)
5. Update `kronos_forecast.json` with DB stock list

**Run:** `python3 scripts/sync_from_db.py`

---

### Task 4: Wire sync into build pipeline

**Objective:** Sync runs automatically before deploy

**Files:**
- Modify: `web/package.json` (prebuild script)

```json
"scripts": {
  "prebuild": "python3 ../scripts/sync_from_db.py",
  "build": "tsc -b && vite build"
}
```

Also update `run_kronos.py` line 24-26 to read stock list from DB instead of `portfolios.json`:
```python
# Before: reads portfolios.json
# After: reads DB
cur.execute("SELECT name, id FROM stocks WHERE status != 'removed'")
stocks = [(r[0], r[1]) for r in cur.fetchall()]
```

---

### Task 5: Create DB-first insert helper

**Objective:** Standardize the insert path so all cron/manual workflows hit DB first

**Files:**
- Create: `scripts/insert_stock_db.py`

```python
"""Usage: python3 scripts/insert_stock_db.py '<json_blob>'
Accepts a JSON string with all stock fields.
Inserts into DB, then runs sync_from_db.py.
"""
```

---

### Task 6: Update cron job prompts

**Objective:** All Divvy cron jobs insert into DB first, then sync

**Files:**
- Modify: 4 cron jobs via `cronjob` tool (update prompt)

Change Deep Dive step 4 from:
> "Add recommended stocks to src/data/stocks.ts"

To:
> "Insert recommended stocks into DB via scripts/insert_stock_db.py, then run scripts/sync_from_db.py"

---

### Task 7: Build, deploy, verify

```bash
python3 scripts/sync_from_db.py
cd web && npm run build
npx sst deploy --stage live
```

Verify at https://d2d7b6u77b6we4.cloudfront.net — all 23 stocks should appear.

---

### Task 8: Re-index

```bash
graphify .
```
