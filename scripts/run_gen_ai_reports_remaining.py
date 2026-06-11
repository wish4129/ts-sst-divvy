#!/usr/bin/env python3
"""Retry AI report generation for the 6 stocks that were missed."""
import os, sys, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

env_path = Path.home() / '.hermes' / '.env'
key = None
for line in open(env_path):
    if line.startswith('DEEPSEEK_API_KEY'):
        key = line.strip().split('=', 1)[1].strip().strip('"').strip("'")
        break
if not key:
    print("DEEPSEEK_API_KEY not found")
    sys.exit(1)
os.environ['DEEPSEEK_API_KEY'] = key

from db import get_db, dict_cursor

PERSONA_CONTEXT = {
    "ares": {"name": "Ares (Aggressive Growth)", "style": "Aggressive Growth - high risk, high reward."},
    "demeter": {"name": "Demeter (Dividend Income)", "style": "Dividend Income - stable, defensive."},
    "athena": {"name": "Athena (Balanced Value)", "style": "Balanced Value - moderate risk."},
}

MISSING = {
    "9393.KL": "Industronics Berhad",
    "7943.KL": "Greentronics Technology Berhad",
    "2097.KL": "Meta Bright Group Berhad",
    "5249.KL": "IOI Properties Group Berhad",
    "5278.KL": "Rhone Ma Holdings Berhad",
    "5703.KL": "Muhibbah Engineering (M) Bhd.",
}
PERSONAS = ["ares", "athena", "demeter"]

db = get_db()
cur = dict_cursor(db)
import urllib.request

total = 0
for code, name in MISSING.items():
    for pid in PERSONAS:
        # Get the stock_analyses id
        cur.execute(
            "SELECT id, score_composite FROM stock_analyses WHERE stock_id=%s AND persona=%s AND score_composite IS NOT NULL AND ai_report IS NULL ORDER BY generated_at DESC LIMIT 1",
            (code, pid)
        )
        row = cur.fetchone()
        if not row:
            continue
        
        score = row["score_composite"]
        analysis_id = row["id"]
        
        # Get stock info
        cur.execute("SELECT name, industry, last_price FROM stocks WHERE id=%s", (code,))
        stock = cur.fetchone()
        stock_name = stock["name"] if stock else name
        industry = stock.get("industry", "N/A") if stock else "N/A"
        price = str(stock.get("last_price", "N/A")) if stock else "N/A"
        
        prompt = f"""Analyze {stock_name} ({code}) for the {PERSONA_CONTEXT[pid]['name']} persona.

Company: {stock_name}
Industry: {industry}
Current Score: {score}/100
Last Price: RM {price}

**Persona:** {pid.upper()} -- {PERSONA_CONTEXT[pid]['style']}

Generate a concise AI analysis report with:
1. **Company Overview** -- Brief business description and market position (2-3 sentences)
2. **Financial Health** -- Key financial metrics and trends
3. **Growth Prospects** -- Growth drivers and catalysts
4. **Risk Assessment** -- Key risks and concerns
5. **Summary** -- Overall assessment for {pid} persona. Buy/Hold/Sell recommendation with brief rationale.

Return as a JSON object with keys: overview, financial_health, growth_prospects, risk_assessment, summary"""

        data = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 1000,
        }
        req = urllib.request.Request(
            "https://api.deepseek.com/v1/chat/completions",
            data=json.dumps(data).encode(),
            headers={"Authorization": f"Bearer {os.environ['DEEPSEEK_API_KEY']}", "Content-Type": "application/json"},
        )
        try:
            resp = urllib.request.urlopen(req, timeout=120)
            result = json.loads(resp.read())
            content = result["choices"][0]["message"]["content"]
            try:
                ai_report = json.loads(content)
            except json.JSONDecodeError:
                ai_report = {"raw": content}
            
            cur.execute(
                "UPDATE stock_analyses SET ai_report=%s, ai_model=%s WHERE id=%s",
                (json.dumps(ai_report), "deepseek-chat", analysis_id)
            )
            db.commit()
            total += 1
            print(f"ok - {code} {name} persona={pid}")
        except Exception as e:
            print(f"FAIL - {code} {pid}: {e}")
            db.rollback()
        sys.stdout.flush()

db.close()
print(f"\nDone. Generated {total} reports for remaining stocks.")
