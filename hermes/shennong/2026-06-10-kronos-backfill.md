# Shennong Research: Kronos Forecast Backfill (16 Missing Stocks)

**Date:** 2026-06-10  
**Task:** t_sh1_kronos_16 — Run Kronos forecasts for 16 stocks missing from kronos_forecasts

## Summary

Successfully generated Kronos 30-day forecasts for all 16 stocks that were missing from the `kronos_forecasts` table. Total stocks covered: 77/77 (100% coverage).

## New Forecasts

| Stock | Code | Status | Score | Last Price | Forecast | 30d Change |
|-------|------|--------|-------|-----------|----------|-----------|
| Bina Darulaman | 6173.KL | revisit | 37 | RM0.20 | RM0.24 | **+21.3%** |
| Lee Swee Kiat Group | 8079.KL | revisit | 59 | RM0.30 | RM0.35 | **+15.6%** |
| Mah Sing Group | 8583.KL | revisit | 66 | RM0.95 | RM1.10 | **+14.7%** |
| Notion VTec | 0083.KL | revisit | 62 | RM0.42 | RM0.48 | **+13.3%** |
| Alliance Bank | 2488.KL | revisit | 68 | RM4.66 | RM5.04 | **+8.1%** |
| Propel Global | 0091.KL | revisit | 35 | RM0.06 | RM0.07 | **+6.9%** |
| Watta Holding | 7226.KL | revisit | 35 | RM0.37 | RM0.39 | **+6.7%** |
| S & F Capital | 8745.KL | revisit | 32 | RM0.06 | RM0.06 | **+5.8%** |
| Titijaya Land | 5239.KL | revisit | 37 | RM0.21 | RM0.21 | +1.9% |
| Aeon Co. (M) | 6599.KL | revisit | 61 | RM1.05 | RM1.07 | +1.5% |
| iCapital.biz | 5108.KL | revisit | 60 | RM2.55 | RM2.59 | +1.5% |
| Asia Brands | 7722.KL | revisit | 50 | RM0.49 | RM0.49 | +1.3% |
| Solid Automotive | 5242.KL | revisit | 40 | RM0.12 | RM0.12 | -1.3% |
| Texchem Resources | 8702.KL | revisit | 28 | RM0.77 | RM0.72 | -7.4% |
| Sarawak Oil Palms | 5126.KL | revisit | 65 | RM4.65 | RM4.06 | -12.8% |
| Tong Herr Resources | 5010.KL | revisit | 35 | RM1.62 | RM1.15 | **-28.8%** |

## Notable Findings

- **10/16 bullish** (positive predicted change), **6/16 bearish** (negative)
- **Strongest bullish**: Bina Darulaman (+21.3%), Lee Swee Kiat (+15.6%), Mah Sing (+14.7%), Notion VTec (+13.3%)
- **Strongest bearish**: Tong Herr Resources (-28.8%, high vol 7.12%), Sarawak Oil Palms (-12.8%)
- **All 77 stocks now covered**: 0 remain missing from kronos_forecasts
- **JSON regenerated**: `data/kronos_forecast.json` updated with all 77 forecasts
