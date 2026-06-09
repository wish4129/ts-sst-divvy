#!/usr/bin/env python3
"""Generate AI reports for 8 universe stocks that have scores but no AI reports.

These are stock_analyses rows where score_composite IS NOT NULL but ai_report IS NULL.
The stocks are not in any persona's holdings, so gen_ai_reports.py skips them.
We need to UPDATE the existing scored rows, not INSERT new ones.
"""
import os, sys, json, urllib.request
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Read API key
env_path = Path.home() / '.hermes' / '.env'
key = None
for line in open(env_path):
    if line.startswith('DEEPSEEK_API_KEY'):
        key = line.strip().split('=', 1)[1].strip().strip('"').strip("'")
        break
if not key:
    print("DEEPSEEK_API_KEY not found in .env")
    sys.exit(1)
os.environ['DEEPSEEK_API_KEY'] = key

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from db import get_db, dict_cursor

MYT = timezone(timedelta(hours=8))

# These are the 8 universe stocks without AI reports (confirmed by DB query)
TARGET_STOCKS = {
    "5040.KL": ("Meridian Berhad", "Property"),
    "5062.KL": ("Hua Yang Berhad", "Property"),
    "5186.KL": ("Malaysia Marine and Heavy Engineering Holdings Berhad", "Oil & Gas"),
    "5209.KL": ("Gas Malaysia Berhad", "Utilities"),
    "5258.KL": ("Bank Islam Malaysia Berhad", "Financial Services"),
    "5592.KL": ("Grand Central Enterprises Bhd", "Consumer"),
    "7006.KL": ("Rhong Khen International Berhad", "Industrial"),
    "8621.KL": ("LPI Capital Bhd", "Insurance"),
}

# Load external data
macro = json.loads((ROOT / "data" / "macro_signals.json").read_text())
fin = json.loads((ROOT / "data" / "stock_financials.json").read_text())
kronos = json.loads((ROOT / "data" / "kronos_forecast.json").read_text()) if (ROOT / "data" / "kronos_forecast.json").exists() else {}
fin_by_code = {}
for name, data in fin.get("stocks", {}).items():
    if "error" not in data:
        fin_by_code[data["code"]] = data

PERSONA_CONTEXT = {
    "ares": {"style": "Aggressive Momentum + Deep Value"},
    "demeter": {"style": "Conservative Dividend Compound"},
    "athena": {"style": "Hybrid GARP"},
}

def generate_ai_report(stock_name, code, industry, fin_data, score_val, ksig, persona):
    price_now = fin_data.get("current_price", "N/A")
    pe = fin_data.get("pe_ratio", "N/A")
    dy = fin_data.get("dividend_yield_pct", "N/A")
    roe = fin_data.get("roe_pct", "N/A")
    de = fin_data.get("de_ratio", "N/A")
    rev_growth = fin_data.get("revenue_growth_yoy_pct", "N/A")
    mcap = fin_data.get("market_cap_m", "N/A")
    kronos_pct = ksig.get("pred_change_pct", "N/A") if ksig else "N/A"
    kronos_low = ksig.get("pred_low", "N/A") if ksig else "N/A"
    kronos_high = ksig.get("pred_high", "N/A") if ksig else "N/A"
    kronos_vol = ksig.get("pred_volatility", "N/A") if ksig else "N/A"

    macro_summary = ", ".join(
        f"{v.get('label','')}: {v.get('value','')} ({v.get('trend','')})"
        for v in list(macro.get("signals", {}).values())[:5]
    ) if macro.get("signals") else "No macro data"

    prompt = f"""You are a Bursa Malaysia equity analyst. Write a comprehensive analysis report for {stock_name} ({code}), a {industry} company listed on Bursa Malaysia.

**Current Data:**
- Price: RM{price_now}
- Market Cap: RM{mcap}M
- P/E Ratio: {pe}x
- Dividend Yield: {dy}%
- ROE (quarterly): {roe}%
- Debt/Equity: {de}x
- Revenue Growth YoY: {rev_growth}%
- Industry Score: {score_val}/100

**Kronos AI 30-Day Forecast:**
- Predicted Change: {kronos_pct}%
- Predicted Range: RM{kronos_low} – RM{kronos_high}
- Volatility: {kronos_vol}%

**Macro Context:**
{macro_summary}

**Persona:** {persona.upper()} — {PERSONA_CONTEXT[persona]['style']}

Write the report in these 7 sections. Be concise but thorough. Use Malaysian English (RM, Bursa, etc.):

1. **Introduction & History** — Brief background of the company, what it does, market position, key milestones
2. **Trend Analysis** — Price trend, revenue trend, industry trend, Kronos forecast direction
3. **Strengths** — Key competitive advantages, financial strengths, macro tailwinds
4. **Weaknesses** — Risks, competitive threats, financial red flags, macro headwinds
5. **Summary** — Overall assessment for {persona} persona. Buy/Hold/Sell recommendation with brief rationale.
6. **Price Target** — Price target (RM), expected timeframe (weeks/months), volatility assessment, hidden risks to monitor
7. **Cut Loss** — Cut loss stop price (RM), percentage loss, trigger conditions

Return the report as a markdown document with 7 sections using `### Section Name` headers."""

    try:
        req = urllib.request.Request(
            "https://api.deepseek.com/chat/completions",
            data=json.dumps({
                "model": "deepseek-v4-pro",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 4096,
            }).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
            },
        )
        resp = urllib.request.urlopen(req, timeout=120)
        body = json.loads(resp.read().decode())
        content = body["choices"][0]["message"]["content"].strip()

        import re as _re
        section_map = {
            "introduction_history": "Introduction & History",
            "trend_analysis": "Trend Analysis",
            "strengths": "Strengths",
            "weaknesses": "Weaknesses",
            "summary": "Summary",
            "price_target": "Price Target",
            "cut_loss": "Cut Loss",
        }
        report = {}
        for section_key, header in section_map.items():
            escaped = _re.escape(header)
            pattern = rf'(?:###\s+{escaped}|[*][*]{escaped}[*][*])\s*\n(.*?)(?=\n(?:###\s|[*][*](?:Introduction|Trend|Strengths|Weaknesses|Summary|Price Target|Cut Loss)[*][*])|\Z)'
            m = _re.search(pattern, content, _re.DOTALL)
            if m:
                report[section_key] = m.group(1).strip()

        required = ["introduction_history", "trend_analysis", "strengths", "weaknesses", "summary", "price_target", "cut_loss"]
        if all(k in report for k in required):
            return report
        # Fallback: try to parse the response differently — use raw content as a single report
        print(f"  WARNING: missing keys for {stock_name}/{persona}: got {list(report.keys())}, using raw content fallback")
        # Store raw content as a simple structured report
        fallback = {
            "introduction_history": content[:300] if len(content) > 300 else content,
            "trend_analysis": "",
            "strengths": "",
            "weaknesses": "",
            "summary": content if len(content) > 300 else "",
            "price_target": "",
            "cut_loss": "",
        }
        return fallback
    except Exception as e:
        print(f"  WARNING: failed for {stock_name}/{persona}: {e}")
        return None

# Process
db = get_db()
cur = dict_cursor(db)
now = datetime.now(MYT)
total = 0

for code, (name, industry) in TARGET_STOCKS.items():
    fin_data = fin_by_code.get(code, {})
    ksig = kronos.get(name, {})
    industry_report = fin_data.get("industry", industry)

    for persona in ["ares", "demeter", "athena"]:
        # Get the score from existing row
        cur.execute(
            "SELECT id, score_composite FROM stock_analyses WHERE stock_id=%s AND persona=%s AND ai_report IS NULL AND score_composite IS NOT NULL ORDER BY generated_at DESC LIMIT 1",
            (code, persona)
        )
        row = cur.fetchone()
        if not row:
            print(f"  {persona:8s} {name:10s} ({code}) — already has AI report or no scored row, skipping")
            continue

        score_val = row["score_composite"]
        print(f"  {persona:8s} {name:10s} ({code}) score={score_val} — generating AI report...", flush=True)
        ai_report = generate_ai_report(name, code, industry_report, fin_data, score_val, ksig, persona)

        if ai_report:
            # UPDATE the existing scored row (critical: do NOT INSERT)
            cur.execute(
                "UPDATE stock_analyses SET ai_report = %s, ai_model = %s WHERE id = %s",
                (json.dumps(ai_report), "deepseek-v4-pro", row["id"])
            )
            if cur.rowcount > 0:
                db.commit()  # Commit immediately so timeouts don't lose progress
                total += 1
                print(f"    OK row {row['id']}", flush=True)
            else:
                print(f"    FAILED to update row {row['id']}", flush=True)
        else:
            print(f"    FAILED to generate", flush=True)

db.commit()
cur.close()
db.close()
print(f"\nDone: generated {total} AI reports at {now.isoformat()}")
