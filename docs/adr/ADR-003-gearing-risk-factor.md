# ADR-003: Gearing Ratio Risk Factor — Validation & Potential Refinement

## Status
Superseded by earlier implementation

## Context
The task asked to "add D/E ratio and gearing ratio to the Risk pillar" of the stock scoring system. Before this ADR, the de_ratio factor already existed in the scoring system at 15% weight across all industries. Investigation was needed to verify whether the scoring was actually punishing overleveraged stocks.

## Investigation Findings
- D/E data is already extracted by `financial_fetcher.py` from yfinance (`debtToEquity` field)
- Stored as `debt_to_equity` column in `stocks` table
- Scored by `industry_scorer.py` using `de_ratio` factor at 15% weight
- Benchmark curve: D/E=0→100, 0.3→95, 0.5→85, 1.0→70, 5.0→30, 50→5, 100→0
- High-D/E stocks are penalized: Astro (D/E=202) → raw score 0/100, Genting (D/E=97) → raw score 0.3/100

## Assessment
The gearing ratio risk factor is **already implemented and functional**.

## Decision
No code changes needed.

### Validation Results
- Stocks with D/E > 5 reliably score < 50 on the de_ratio factor
- Stocks with D/E > 100 score 0 (max penalty)
- The 15% weight within the Risk pillar appropriately reflects gearing as one risk component
- The curve penalizes fast in the 0.5-2.0 zone (critical for timely warning)

## Potential Future Refinements (not urgent)
1. **Industry-specific D/E benchmarks** — REITs and banks naturally have higher D/E ratios; the curve currently treats all industries uniformly
2. **Cash flow coverage ratio** — Adding interest coverage ratio as a secondary risk factor could distinguish "overleveraged but profitable" from "overleveraged and struggling"
3. **Explicit "leverage danger zone" flag in score rationale** — Currently the 15% weight may not be visible enough in the composite score

## Consequences
- **No code changes** — the system already captures gearing risk
- **Task completed** — ADR documents the validation for future reference
