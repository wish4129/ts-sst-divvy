# Divvy — Domain Glossary

## Core Concepts
- **persona** — Investment strategy: Ares (momentum), Demeter (dividends), Athena (GARP)
- **score_composite** — GREATEST(stocks.score_composite, stock_analyses.score_composite)
- **battle** — Multi-persona simulation trading Bursa stocks, Wed-Fri every 30min
- **pending_analyses** — Queue table for async stock analysis jobs, processed hourly
- **stock_analyses** — Per-stock analysis results, UNIQUE(stock_id, persona), ON CONFLICT DO UPDATE

## Cron Jobs
- Battle: Wed-Fri 9am-5pm every 30min
- Score Alert: Daily 9am
- Screener: Mon 9am (new Bursa candidates)
- Deep Dive: Mon 10am (weekly analysis)
- Random Analysis: Weekdays 2pm (3 unanalyzed stocks)
- Pending Analysis: Every 60min (queue-first, random fallback)
- Kronos Forecast: via run_kronos.py

## Data Sources
- Stocks table is source of truth for scores
- yfinance + Kronos for financial data
- Supabase (ceyqewaixcijbmdtbdlr) for all DB operations
- industry_scorer.py skips stocks not in stock_financials.json

## Project
- Repo: ~/xiongit/divvy
- Stack: SST v3 + React + Recharts + Supabase
- Domain: d2d7b6u77b6we4.cloudfront.net
