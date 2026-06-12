#!/usr/bin/env python3
"""Generate AI reports for specific stock+persona combinations that have scores but no AI report."""
import os, sys, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent  # scripts/ dir
sys.path.insert(0, str(ROOT))

# Must import before db to ensure DEEPSEEK_API_KEY is set
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

from db import get_db, dict_cursor
from persona_db import get_all_stocks_dict
import urllib.request

PERSONA_CONTEXT = {
    "ares": {
        "name": "Ares (Aggressive Growth)",
        "style": "Aggressive Growth - high risk, high reward. Prefers small-cap, high-growth opportunities with momentum.",
    },
    "demeter": {
        "name": "Demeter (Dividend Income)",
        "style": "Dividend Income - stable, defensive. Prefers dividend-paying blue chips with strong fundamentals.",
    },
    "athena": {
        "name": "Athena (Balanced Value)",
        "style": "Balanced Value - moderate risk, quality at fair price. Prefers established companies with competitive advantages.",
    },
}

# Load data
# Load all stocks from DB
all_stocks = get_all_stocks_dict()
macro = json.loads((ROOT / ".." / "data" / "macro_signals.json").read_text())
fin = json.loads((ROOT / ".." / "data" / "stock_financials.json").read_text())
kronos_path = ROOT / ".." / "data" / "kronos_forecast.json"
kronos = json.loads(kronos_path.read_text()) if kronos_path.exists() else {}

fin_by_code = {}
for name, data in fin.get("stocks", {}).items():
    if "error" not in data:
        fin_by_code[data["code"]] = data

db = get_db()
cur = dict_cursor(db)

# Get scores
cur.execute("SELECT stock_id, MAX(score_composite) as score FROM stock_analyses GROUP BY stock_id")
score_by_code = {}
for r in cur.fetchall():
    score_by_code[r["stock_id"]] = {"composite": int(r["score"]) if r["score"] else 0, "macro_adjustment": 0}

# Get rows that need AI reports
cur.execute("""
    SELECT sa.id, sa.stock_id, sa.persona, sa.score_composite, sa.generated_at
    FROM stock_analyses sa
    JOIN stocks s ON s.id = sa.stock_id
    WHERE s.status NOT IN ('removed', 'data_missing') AND sa.score_composite IS NOT NULL AND sa.ai_report IS NULL
    ORDER BY sa.persona, sa.score_composite
""")
missing_rows = cur.fetchall()
print(f"Found {len(missing_rows)} stock_analyses rows needing AI reports")
sys.stdout.flush()

# Build a lookup from stock_id -> stock name
code_to_name = {}
for name, info in all_stocks.items():
    c = info.get("code", "")
    if c:
        code_to_name[c] = name

total_generated = 0
for row in missing_rows:
    code = row["stock_id"]
    pid = row["persona"]
    score = row["score_composite"]
    name = code_to_name.get(code, code)
    info = all_stocks.get(name, {})
    score_data = score_by_code.get(code, {"composite": int(score) if score else 0})
    fin_data = fin_by_code.get(code, {})
    ksig = kronos.get(name, {})
    
    print(f"{pid:8s} {name:15s} ({code:10s}) score={str(score):6s} generating...")
    sys.stdout.flush()
    
    prompt = f"""Analyze {name} ({code}) for the {PERSONA_CONTEXT[pid]['name']} persona.

Company: {info.get('name', name)}
Industry: {info.get('industry', 'N/A')}
Current Score: {score}/100
Last Price: RM {info.get('last_price', info.get('price', 'N/A'))}

Financial Data Available: {bool(fin_data)}
Kronos Forecast Available: {bool(ksig)}

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
        headers={
            "Authorization": f"Bearer {os.environ['DEEPSEEK_API_KEY']}",
            "Content-Type": "application/json",
        },
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
            """UPDATE stock_analyses SET ai_report = %s, ai_model = %s
               WHERE id = %s""",
            (json.dumps(ai_report), "deepseek-chat", row["id"])
        )
        db.commit()
        total_generated += 1
        print(f"  ok - generated for {name} ({code}) persona={pid}")
    except Exception as e:
        print(f"  FAILED: {e}")
        db.rollback()
    sys.stdout.flush()

db.close()
print(f"\nDone. Generated {total_generated} AI reports total.")
