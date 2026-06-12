# ADR-001: Simplify Stock Scoring — Drop 4-Pillar Display Weights, Use Raw Composite

## Status
Accepted

## Context

The Divvy scoring system has two parallel score representations that are inconsistently maintained:

### Current Architecture

**Data flow:**
```
industry_scorer.py → stocks.score_composite / stocks.score_subs / stock_analyses.score_breakdown
                                           ↓
                             sync_from_db.py → web/src/data/stocks.ts (frontend)
                                           ↓
                             4-pillar bars on StockDetail.tsx
```

**The composite score** (used for all real decisions: portfolio ranking, stock sorting, score badges):
- Computed as `sum(weighted_factor_raw_scores) + macro_adjustment`
- Factors weighted per-industry (e.g., Banking: dividend=25%, growth=25%, quality=35%, risk=15%)
- Range: 0–100
- Written to `stocks.score_composite` and `stock_analyses.score_composite`

**The 4-pillar sub-scores** (display-only, shown as 4 progress bars on StockDetail):
- `dividend`: max 40 — derived by summing `dividend_yield.raw` into `score_subs.dividend`, then capped at 40
- `growth`: max 30 — derived from `revenue_growth_yoy.raw` into `score_subs.growth`, capped at 30
- `quality`: max 20 — derived from `roe.raw` + `gross_margin.raw` into `score_subs.quality`, capped at 20
- `risk`: max 10 — derived from `de_ratio.raw` into `score_subs.risk`, capped at 10

### Problems Identified

1. **The 4-pillar max values (40/30/20/10) are arbitrary** — they correspond to no real weighting system. The actual factor weights (25/25/35/15) are different numbers used only for composite calculation, and they sum to 100 only coincidentally in the default config.

2. **No test or user relies on the 4-pillar sub-scores** — only `score_composite` is used in:
   - Portfolio manager scoring logic
   - Score badges (ScoreBadge component)
   - Stock sorting in sync_from_db (`ORDER BY score_composite DESC`)
   - Status determination (≥70 = active)

3. **Maintenance burden** — any change to factor weights in `industry_matrix.json` requires manually updating the `factor_to_sub` mapping and cap values (40/30/20/10) in `industry_scorer.py` line 162-165, plus the hardcoded `max` values in `StockDetail.tsx` lines 273-276.

4. **Misleading UX** — the 4 "pillars" imply dimension-specific scores, but in reality they're just loosely-clustered factor groups with arbitrary caps. A stock with strong dividend yield but weak everything else shows "Dividend: 25/40" which misrepresents the actual 25% weight.

### Options Considered

#### Option A: Drop pillars entirely, show only composite score
- Remove `score_subs` from DB writes
- Remove 4-pillar bars from StockDetail
- Replace with simple composite score badge (already exists) + factor breakdown table (already shown in separate section)
- **Pro**: Simplest change, removes all maintenance burden
- **Con**: Loses the visual breakdown that some users glance at

#### Option B: Make pillars reflect actual weights
- Pillar max = weight percentage (25/25/35/15)
- Sub-scores = weighted contributions, not raw sums
- **Pro**: Consistent, meaningful
- **Con**: Still display-only, adds complexity to keep in sync, and weights vary by industry anyway

#### Option C: Keep only factor breakdown (already exists)
- The "Factor Score Breakdown" section on StockDetail already shows each factor with its weighted score
- This is the real data users need — what drove the composite up or down
- **Pro**: Zero new code, already implemented, data-driven
- **Con**: Users lose the summarised 4-bar visualization

## Decision

**Adopt Option A — Drop the 4-pillar display sub-scores entirely.**

Rationale:
1. The industry_matrix.json already defines per-factor weights that map directly to the composite score — the 4-pillar grouping adds no information not already visible in the factor breakdown
2. The composite score is what matters: it's what determines buy/sell decisions, ranking, and badge color
3. Removing the display artifact eliminates a whole class of maintenance burden (cap values, factor_to_sub mapping that can drift from matrix weights)
4. The Factor Score Breakdown section already shows every factor with its computed and weighted value

## Consequences

### Easier
- `industry_scorer.py` no longer computes or writes `score_subs` — remove the computation block (lines ~148-176)
- `StockDetail.tsx` no longer renders the 4-pillar progress bars — remove the "Score Breakdown" card
- `sync_from_db.py` no longer reads `score_subs` or writes `score_dividend/growth/quality/risk` into the TS data
- Any future change to factor weights in `industry_matrix.json` doesn't require UI updates
- The DB column `stocks.score_subs` can be deprecated (keep for historical data but stop writing)

### Harder
- Users lose the 4-bar visual summary — they see only the composite badge + raw factor table
- Some may interpret "fewer visuals" as "less capability"
- The DB column `stocks.score_subs` becomes dead data for any stock scored after this change

### Data Schema Changes
- **Write side** (`industry_scorer.py`): Stop computing `subs` dict, remove `score_subs` from `UPDATE stocks SET`
- **Read side** (`sync_from_db.py`): Stop reading `score_subs`, drop `score_dividend/growth/quality/risk` from generated TS
- **Frontend** (`StockDetail.tsx`): Remove the "Score Breakdown" section (lines ~269-285), remove ScoreBadge integration (just rely on existing ScoreBadge in the header)
- **Frontend data** (`stocks.ts` interface): Remove `StockScore` interface fields `dividend`, `growth`, `quality`, `risk` — keep only `composite`

## Implementation Plan

1. `scripts/industry_scorer.py`:
   - Remove `factor_to_sub` mapping
   - Remove `subs` dict computation
   - Remove `score_subs` from the UPDATE query
   - Keep `score_composite`, `score_breakdown` (factor detail), and `decision_rationale`

2. `scripts/sync_from_db.py`:
   - Remove `score_subs_raw` from SELECT
   - Remove `score_dividend`, `score_growth`, `score_quality`, `score_risk` from output
   - Remove `StockScore.quality/risk/dividend/growth` from TypeScript interface
   - Regenerate `stocks.ts`

3. `web/src/pages/StockDetail.tsx`:
   - Remove the "Score Breakdown" 4-bar section
   - The header already shows ScoreBadge (composite) — that's sufficient
   - The Factor Score Breakdown table already shows per-factor detail

4. `web/src/components/ScoreBadge.tsx` — no changes needed

5. Regenerate stocks.ts via sync_from_db

6. Run full test suite to verify nothing breaks
