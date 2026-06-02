#!/usr/bin/env python3
"""Deep Analysis Generator — generates AI reports for all stocks.

Data sources:
  - stocks.ts          → financial data + scores (single source of truth, curated)
  - portfolios.json    → persona holdings for Phase 1 portfolio analysis
  - macro_signals.json → macro context (independently maintained)
  - stocks table (DB)  → stock registry for Phase 2 watchlist

NO yfinance dependency. All stock data comes from our curated stocks.ts file.

Writes: stock_analyses table (keeps history — no UNIQUE constraint).

Two phases:
  1. Portfolio holdings — AI reports for stocks in persona portfolios
  2. Watchlist — AI reports for all other active/revisit stocks

AI reports use markdown-based ## header parsing. Retries up to 2 times on failure.
"""
import sys, json, re, os, time
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Force unbuffered output for cron runs (available in Python 3.7+)
try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from db import get_db

MYT = timezone(timedelta(hours=8))

# ── Persona strategies ──
PERSONAS = {
    "ares": {
        "style": "Aggressive Momentum + Deep Value",
        "philosophy": "Strike fast. Momentum-driven entries, cut losers at -12%. "
                      "No take-profit — let compounders run. Max 25% single bet. "
                      "Kronos signals override fundamentals when momentum is strong.",
    },
    "demeter": {
        "style": "Conservative Dividend Compound",
        "philosophy": "Steady harvest. Dividend compounding is primary return driver. "
                      "10% cash buffer. Trim if DY < 3%. Dividend cut >20% triggers review. "
                      "Max 35% single bet.",
    },
    "athena": {
        "style": "Hybrid GARP (Growth at Reasonable Price)",
        "philosophy": "Tactical GARP. Balance growth with valuation. Sell 50% at +25%, "
                      "full exit at +40%. Dip buy -10% (30d cooldown). Max 30% single bet.",
    },
}


# ═══════════════════════════════════════════════════════════════
# Parse stocks.ts — our single source of truth for financial data
# ═══════════════════════════════════════════════════════════════

# Map short codes (MAYBANK) → ticker codes (1155.KL)
SHORT_TO_TICKER = {
    'MAYBANK': '1155.KL', 'AXREIT': '5106.KL', 'YTLPOWR': '6742.KL',
    'INSAS': '3379.KL', 'LIIHEN': '7089.KL', 'SCIENTEX': '4731.KL',
    'GENETEC': '0104.KL', 'KLK': '2445.KL', 'INARI': '0166.KL',
    'SIME': '4197.KL', 'MAGNI': '7087.KL', 'MBMR': '5983.KL',
    'AME': '5293.KL', 'DELEUM': '5132.KL', 'WASCO': '5142.KL',
    'KIPREIT': '5280.KL', 'INTA': 'INTA.KL',
    'RHB': '1066.KL', 'PADINI': '7052.KL',
    'GAMUDA': '5398.KL', 'MATRIX': '5236.KL',
}


def parse_stocks_ts() -> dict:
    """Parse web/src/data/stocks.ts into a dict keyed by ticker code.
    
    Returns: { '1155.KL': { name, industry, price, pe, dy, roe, de,
                             rev_growth, eps_growth, beta, fcf, high52, low52,
                             score_composite, score_subs } }
    """
    ts_path = ROOT / "web" / "src" / "data" / "stocks.ts"
    content = ts_path.read_text()
    
    # Extract each stock block
    stock_pattern = re.compile(
        r"code:\s*'(\w+)'.*?"
        r"name:\s*'([^']+)'.*?"
        r"industry:\s*'([^']+)'.*?"
        r"lastPrice:\s*([\d.]+).*?"
        r"dividendYield:\s*([\d.]+).*?"
        r"score:\s*\{\s*composite:\s*(\d+).*?"
        r"peRatio:\s*([\d.-]+).*?"
        r"roe:\s*([\d.-]+).*?"
        r"debtToEquity:\s*([\d.-]+).*?"
        r"revenueGrowthYoY:\s*([\d.-]+)",
        re.DOTALL
    )
    
    result = {}
    for m in stock_pattern.finditer(content):
        short_code = m.group(1)
        ticker = SHORT_TO_TICKER.get(short_code, short_code + '.KL')
        
        result[ticker] = {
            "name": m.group(2),
            "industry": m.group(3),
            "price": float(m.group(4)),
            "dy": float(m.group(5)),
            "score_composite": int(m.group(6)),
            "pe": float(m.group(7)),
            "roe": float(m.group(8)),
            "de": float(m.group(9)),
            "rev_growth": float(m.group(10)),
            # Estimated/extracted from notes or reasonable defaults
            "eps_growth": 0.0,
            "beta": 0.5,
            "fcf": 0,
            "high52": 0.0,
            "low52": 0.0,
            "mcap": 0.0,
        }
    
    return result


# ═══════════════════════════════════════════════════════════════
# AI Report Generation (markdown-based, no yfinance)
# ═══════════════════════════════════════════════════════════════

SECTION_MAP = {
    "introduction": "introduction_history", "history": "introduction_history",
    "trend": "trend_analysis", "strength": "strengths", "weakness": "weaknesses",
    "summary": "summary", "target": "target",
}


def parse_markdown_report(content: str) -> dict | None:
    """Parse ## header sections from DeepSeek markdown response."""
    blocks = re.split(r'\n(?=##\s)', content)
    sections = {}
    
    for block in blocks:
        m = re.match(r'##\s+(.+?)(?:\s*\n|$)', block)
        if not m:
            lower = block.lower()
            if any(kw in lower for kw in ['introduction', 'history', 'background']):
                sections["introduction_history"] = block.strip()
            elif 'trend' in lower:
                sections["trend_analysis"] = block.strip()
            continue
        
        header = m.group(1).strip()
        text = block[m.end():].strip()
        for keyword, key in SECTION_MAP.items():
            if keyword in header.lower():
                sections[key] = text
                break
    
    required = ["introduction_history", "trend_analysis", "strengths", "weaknesses", "summary"]
    if any(k not in sections for k in required):
        return None
    
    # Split target into price_target + cut_loss
    if "target" in sections:
        target_text = sections.pop("target")
        lines = target_text.split("\n")
        pt_lines, cl_lines = [], []
        in_cl = False
        for line in lines:
            low = line.lower()
            if any(kw in low for kw in ["cut loss", "stop loss", "cut-loss", "max loss", "risk management"]):
                in_cl = True
            if in_cl:
                cl_lines.append(line)
            else:
                pt_lines.append(line)
        sections["price_target"] = "\n".join(pt_lines).strip() or target_text
        sections["cut_loss"] = "\n".join(cl_lines).strip() or ""
    else:
        sections["price_target"] = ""
        sections["cut_loss"] = ""
    
    return sections


def generate_ai_report(stock_data: dict, macro_str: str, persona: str, max_retries: int = 2) -> dict | None:
    """Call DeepSeek v4 Pro to produce an AI analysis report.
    
    Args:
        stock_data: dict with keys: code, name, industry, price, pe, dy, roe, de,
                    rev_growth, eps_growth, beta, high52, low52, fcf, mcap, score_composite
        macro_str: formatted macro context string
        persona: 'ares', 'demeter', or 'athena'
        max_retries: number of retry attempts
    
    Returns: dict with 7 keys (introduction_history, trend_analysis, strengths, 
             weaknesses, summary, price_target, cut_loss) or None
    """
    # API key: try env first, then fallback to ~/.hermes/.env
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        env_file = Path.home() / ".hermes" / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if "DEEPSEEK_API_KEY" in line and not line.startswith("#"):
                    api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    if not api_key:
        return None
    
    ps = PERSONAS[persona]
    sd = stock_data
    code = sd["code"]
    name = sd["name"]
    
    prompt = f"""You are a Bursa Malaysia analyst for the {persona.upper()} persona ({ps['style']}).

Write a concise analysis with EXACTLY these ## headers:

## Introduction & History
## Trend Analysis
## Strengths
## Weaknesses
## Summary
## Target

STOCK: {name} ({code}) — {sd.get('industry', '')}
Price: RM{sd.get('price', 'N/A')} | P/E: {sd.get('pe', 'N/A')}x | DY: {sd.get('dy', 'N/A')}%
ROE: {sd.get('roe', 'N/A')}% | D/E: {sd.get('de', 'N/A')}x | Beta: {sd.get('beta', 'N/A')}
Rev Growth: {sd.get('rev_growth', 'N/A')}% | Score: {sd.get('score_composite', 50)}/100
Macro: {macro_str}

Strategy: {ps['philosophy']}

Strengths/Weaknesses: use "- " bullet points.
Target: include price target (RM), cut loss (RM), timeframe, hidden risks.
Malaysian English. Be specific with the numbers provided."""

    for attempt in range(max_retries + 1):
        try:
            import urllib.request
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
                    "Authorization": f"Bearer {api_key}",
                },
            )
            resp = urllib.request.urlopen(req, timeout=120)
            body = json.loads(resp.read().decode())
            content = body["choices"][0]["message"].get("content", "").strip()
            
            if not content:
                if attempt < max_retries:
                    time.sleep(2)
                    continue
                return None
            
            report = parse_markdown_report(content)
            if report:
                return report
            
            if attempt < max_retries:
                time.sleep(2)
                continue
            return None
            
        except Exception as e:
            if attempt < max_retries:
                time.sleep(2)
                continue
            print(f"  ⚠ AI failed for {name}/{persona} after {max_retries+1} attempts: {e}", flush=True)
            return None
    
    return None


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════

def main():
    # Load data
    print("Loading data...", flush=True)
    stocks_data = parse_stocks_ts()
    print(f"  Parsed {len(stocks_data)} stocks from stocks.ts", flush=True)
    
    # Load portfolios
    pf_path = ROOT / "scripts" / "portfolios.json"
    if pf_path.exists():
        pf = json.loads(pf_path.read_text())
    else:
        pf = {"personas": {"ares": {"holdings": {}}, "demeter": {"holdings": {}}, "athena": {"holdings": {}}},
              "stocks": {}}
    
    # Load macro
    macro_path = ROOT / "data" / "macro_signals.json"
    if macro_path.exists():
        macro = json.loads(macro_path.read_text())
        signals = macro.get("signals", {})
        macro_str = "; ".join(
            f"{k}: {v.get('value', 'N/A')} ({v.get('trend', 'flat')})"
            for k, v in list(signals.items())[:6] if isinstance(v, dict)
        )
    else:
        macro_str = "No macro data available"
        signals = {}
    
    # DB
    db = get_db()
    cur = db.cursor()
    now = datetime.now(MYT)
    
    generated = 0
    generated_ai = 0
    
    # ── Phase 1: Portfolio holdings ──
    print("\n── Phase 1: Portfolio Holdings ──", flush=True)
    portfolio_codes = set()
    
    for pid in ["ares", "demeter", "athena"]:
        persona = pf["personas"].get(pid, {"holdings": {}})
        for name, holding in persona["holdings"].items():
            info = pf.get("stocks", {}).get(name, {})
            code = info.get("code", "")
            if not code:
                continue
            portfolio_codes.add(code)
            
            sd = stocks_data.get(code)
            if not sd:
                print(f"  {pid:8s} {name:20s} ({code}) — no data in stocks.ts, skipping", flush=True)
                continue
            
            ai_report = generate_ai_report(sd, macro_str, pid)
            
            cur.execute(
                """INSERT INTO stock_analyses (stock_id, persona, score_composite, score_breakdown,
                   decision_rationale, kronos_signal, macro_context, ai_report, ai_model)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (code, pid, sd["score_composite"],
                 json.dumps({}),
                 json.dumps({"sections": {}, "sources": {}}),
                 json.dumps({}),
                 json.dumps(signals),
                 json.dumps(ai_report) if ai_report else None,
                 "deepseek-v4-pro" if ai_report else None)
            )
            generated += 1
            if ai_report:
                generated_ai += 1
                print(f"  {pid:8s} {name:20s} ({code}) ✓ AI", flush=True)
            else:
                print(f"  {pid:8s} {name:20s} ({code}) ✗ no AI", flush=True)
    
    # ── Phase 2: Watchlist stocks ──
    cur.execute("SELECT id, name, industry FROM stocks WHERE status != 'removed' ORDER BY id")
    watchlist = [(r[0], r[1], r[2] or "") for r in cur.fetchall() if r[0] not in portfolio_codes]
    
    if watchlist:
        print(f"\n── Phase 2: Watchlist ({len(watchlist)} stocks) ──", flush=True)
        
        for code, name, industry in watchlist:
            sd = stocks_data.get(code)
            if not sd:
                print(f"  {name:30s} ({code}) — no data in stocks.ts, skipping", flush=True)
                continue
            
            for pid in ["ares", "demeter", "athena"]:
                ai_report = generate_ai_report(sd, macro_str, pid)
                
                if ai_report:
                    cur.execute(
                        """INSERT INTO stock_analyses (stock_id, persona, score_composite, score_breakdown,
                           decision_rationale, kronos_signal, macro_context, ai_report, ai_model)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (code, pid, sd["score_composite"],
                         json.dumps({}),
                         json.dumps({"sections": {}, "sources": {}}),
                         json.dumps({}),
                         json.dumps(signals),
                         json.dumps(ai_report),
                         "deepseek-v4-pro")
                    )
                    generated += 1
                    generated_ai += 1
                    print(f"  {pid:8s} {name:30s} ({code}) ✓ AI", flush=True)
    
    db.commit()
    cur.close()
    db.close()
    
    # Update statuses based on scores
    print(f"\n── Updating statuses (≥70 = active) ──", flush=True)
    db2 = get_db()
    cur2 = db2.cursor()
    cur2.execute("""
        UPDATE stocks SET status = CASE 
            WHEN id IN (SELECT stock_id FROM stock_analyses GROUP BY stock_id HAVING max(score_composite) >= 70) 
            THEN 'active' ELSE 'revisit' END
        WHERE status != 'removed'
    """)
    updated = cur2.rowcount
    db2.commit()
    cur2.close()
    db2.close()
    
    print(f"\n✓ Generated {generated} analyses ({generated_ai} with AI reports)")
    print(f"✓ Updated {updated} stock statuses")
    print(f"✓ Completed at {now.isoformat()}")


if __name__ == "__main__":
    main()
