#!/usr/bin/env python3
"""Read DEEPSEEK_API_KEY from Hermes .env and run deep analysis directly."""
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

# Add scripts dir to path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from db import get_db, dict_cursor

MYT = timezone(timedelta(hours=8))

# Load data
pf = json.loads((ROOT / "scripts" / "portfolios.json").read_text())
scores = json.loads((ROOT / "data" / "stock_scores.json").read_text())
macro = json.loads((ROOT / "data" / "macro_signals.json").read_text())
fin = json.loads((ROOT / "data" / "stock_financials.json").read_text())
kronos = json.loads((ROOT / "data" / "kronos_forecast.json").read_text()) if (ROOT / "data" / "kronos_forecast.json").exists() else {}

score_by_code = {s["code"]: s for s in scores["scores"]}
fin_by_code = {}
for name, data in fin.get("stocks", {}).items():
    if "error" not in data:
        fin_by_code[data["code"]] = data

PERSONA_CONTEXT = {
    "ares": {"style": "Aggressive Momentum + Deep Value"},
    "demeter": {"style": "Conservative Dividend Compound"},
    "athena": {"style": "Hybrid GARP"},
}

def generate_ai_report(stock_name, stock_info, fin_data, score_data, ksig, macro_signals, persona):
    code = stock_info["code"]
    industry = stock_info.get("industry", "")
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
    score_comp = score_data.get("composite", "N/A")
    score_macro = score_data.get("macro_adjustment", 0)
    
    macro_summary = ", ".join(
        f"{v.get('label','')}: {v.get('value','')} ({v.get('trend','')})"
        for v in list(macro_signals.values())[:5]
    ) if macro_signals else "No macro data"
    
    prompt = f"""You are a Bursa Malaysia equity analyst. Write a comprehensive analysis report for {stock_name} ({code}), a {industry} company listed on Bursa Malaysia.

**Current Data:**
- Price: RM{price_now}
- Market Cap: RM{mcap}M
- P/E Ratio: {pe}x
- Dividend Yield: {dy}%
- ROE (quarterly): {roe}%
- Debt/Equity: {de}x
- Revenue Growth YoY: {rev_growth}%
- Industry Score: {score_comp}/100 (Macro Adj: {score_macro:+})

**Kronos AI 30-Day Forecast:**
- Predicted Change: {kronos_pct}%
- Predicted Range: RM{kronos_low} – RM{kronos_high}
- Volatility: {kronos_vol}%

**Macro Context:**
{macro_summary}

**Persona:** {persona.upper()} — {PERSONA_CONTEXT[persona]['style']}

Write the report in these 6 sections. Be concise but thorough. Use Malaysian English (RM, Bursa, etc.):

1. **Introduction & History** — Brief background of the company, what it does, market position, key milestones
2. **Trend Analysis** — Price trend, revenue trend, industry trend, Kronos forecast direction
3. **Strengths** — Key competitive advantages, financial strengths, macro tailwinds
4. **Weaknesses** — Risks, competitive threats, financial red flags, macro headwinds
5. **Summary** — Overall assessment for {persona} persona. Buy/Hold/Sell recommendation with brief rationale.
6. **Target** — Price target (RM), cut loss point (RM), expected timeframe (weeks/months), volatility assessment, hidden risks to monitor

Return the report as a markdown document with 6 sections using `### Section Name` headers. Follow this EXACT format — copy the structure, not the content:

EXAMPLE OUTPUT:
### Introduction & History
Maybank is Malaysia's largest bank by assets, founded in 1960. Market leader in retail and Islamic banking across ASEAN.

### Trend Analysis
Revenue grew 8% YoY driven by NIM expansion. Kronos forecasts +5.2% with moderate volatility.

### Strengths
Strong deposit franchise, 6% dividend yield, well-capitalized with CET1 above 15%.

### Weaknesses
Loan growth slowing, exposure to Malaysia's political risk, fintech disruption threat.

### Summary
BUY for Demeter. Defensive yield play with stable earnings and strong capital buffer. Fits conservative dividend strategy.

### Target
- Price target: RM11.20 (+15% upside)
- Cut loss: RM9.20 (-5.5%)
- Timeframe: 3-6 months
- Volatility: Low (beta 0.85)
- Hidden risks: OPR cuts compressing NIM, asset quality deterioration in SME portfolio

Now write the actual report for {stock_name}:"""

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
        resp = urllib.request.urlopen(req, timeout=90)
        body = json.loads(resp.read().decode())
        content = body["choices"][0]["message"]["content"].strip()
        
        # Parse markdown sections: ### Section Name or **Section Name**\n[content]...
        import re as _re
        section_map = {
            "introduction_history": "Introduction & History",
            "trend_analysis": "Trend Analysis",
            "strengths": "Strengths",
            "weaknesses": "Weaknesses",
            "summary": "Summary",
            "target": "Target",
        }
        report = {}
        for section_key, header in section_map.items():
            # Try ### Header first, then **Header**
            escaped = _re.escape(header)
            pattern = rf'(?:###\s+{escaped}|[*][*]{escaped}[*][*])\s*\n(.*?)(?=\n(?:###\s|[*][*](?:Introduction|Trend|Strengths|Weaknesses|Summary|Target)[*][*])|\Z)'
            m = _re.search(pattern, content, _re.DOTALL)
            if m:
                report[section_key] = m.group(1).strip()
        
        required = ["introduction_history", "trend_analysis", "strengths", "weaknesses", "summary", "target"]
        if all(k in report for k in required):
            return report
        
        print(f"  ⚠ AI report missing keys for {stock_name}: got {list(report.keys())}")
        return None
    except Exception as e:
        print(f"  ⚠ AI report failed for {stock_name}: {e}")
        return None

# Run
db = get_db()
cur = dict_cursor(db)
now = datetime.now(MYT)
total = 0

for pid in ["ares", "demeter", "athena"]:
    persona = pf["personas"][pid]
    for name, holding in persona["holdings"].items():
        info = pf["stocks"].get(name, {})
        code = info["code"]
        score_data = score_by_code.get(code, {})
        fin_data = fin_by_code.get(code, {})
        ksig = kronos.get(name, {})
        
        # Check if we already have an AI report for this stock+persona
        cur.execute(
            "SELECT 1 FROM stock_analyses WHERE stock_id=%s AND persona=%s AND ai_report IS NOT NULL ORDER BY generated_at DESC LIMIT 1",
            (code, pid)
        )
        has_ai = cur.fetchone()
        
        if has_ai:
            print(f"  {pid:8s} {name:10s} ({code}) — ✓ already has AI report, skipping")
            continue
        
        print(f"  {pid:8s} {name:10s} ({code}) — generating AI report...")
        ai_report = generate_ai_report(name, info, fin_data, score_data, ksig, macro.get("signals", {}), pid)
        
        if ai_report:
            # Update the latest scored row (from run_deep_analysis.py) instead of inserting new row
            cur.execute(
                """UPDATE stock_analyses SET ai_report = %s, ai_model = %s
                   WHERE id = (
                     SELECT id FROM stock_analyses
                     WHERE stock_id = %s AND persona = %s AND score_composite IS NOT NULL
                     ORDER BY generated_at DESC LIMIT 1
                   )""",
                (json.dumps(ai_report), "deepseek-v4-pro", code, pid)
            )
            if cur.rowcount == 0:
                # No scored row exists — insert standalone
                cur.execute(
                    "INSERT INTO stock_analyses (stock_id, persona, ai_report, ai_model) VALUES (%s,%s,%s,%s)",
                    (code, pid, json.dumps(ai_report), "deepseek-v4-pro")
                )
            total += 1
            print(f"    ✓ done")
        else:
            print(f"    ✗ failed")

db.commit()
cur.close()
db.close()
print(f"\n✓ Generated {total} AI reports at {now.isoformat()}")
