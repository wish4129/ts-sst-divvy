#!/usr/bin/env python3
"""Generate AI reports for stock_analyses rows where ai_report IS NULL.

Reads all data from DB (no JSON files). Updates existing rows.
Batches to max_reports per run to stay within cron time limits.
"""
import sys, json, os, time, re
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.stdout.reconfigure(line_buffering=True)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from db import get_db, dict_cursor

MYT = timezone(timedelta(hours=8))

# ── Persona contexts ──
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


def get_api_key() -> str:
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not key:
        env_file = Path.home() / ".hermes" / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if "DEEPSEEK_API_KEY" in line and not line.startswith("#"):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    return key


def generate_ai_report(stock_data: dict, macro_str: str, persona: str, max_retries: int = 2) -> dict | None:
    api_key = get_api_key()
    if not api_key:
        return None

    ps = PERSONAS[persona]
    sd = stock_data
    code = sd["code"]
    name = sd["name"]

    # Extract financial data from DB JSONB columns
    fin = sd.get("financials", {})
    pe = fin.get("pe_ratio", "N/A") if isinstance(fin, dict) else "N/A"
    dy = fin.get("dividend_yield_pct", "N/A") if isinstance(fin, dict) else "N/A"
    roe = fin.get("roe_pct", "N/A") if isinstance(fin, dict) else "N/A"
    de = fin.get("de_ratio", "N/A") if isinstance(fin, dict) else "N/A"
    rev_growth = fin.get("revenue_growth_yoy_pct", "N/A") if isinstance(fin, dict) else "N/A"
    
    prompt = f"""You are a Bursa Malaysia analyst for the {persona.upper()} persona ({ps['style']}).

Write a concise analysis with EXACTLY these ## headers:

## Introduction & History
## Trend Analysis
## Strengths
## Weaknesses
## Summary
## Target

STOCK: {name} ({code}) — {sd.get('industry', '')}
Price: RM{sd.get('last_price', 'N/A')} | P/E: {pe}x | DY: {dy}%
ROE: {roe}% | D/E: {de}x | Rev Growth: {rev_growth}%
Market Cap: RM{sd.get('market_cap', 'N/A')} | Score: {sd.get('score_composite', 50)}/100
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


def main(max_reports: int = 20):
    now = datetime.now(MYT)
    print(f"=== AI Report Generator ===")
    print(f"Start: {now.isoformat()}")
    print(f"Max reports this run: {max_reports}")

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

    api_key = get_api_key()
    if not api_key:
        print("ERROR: DEEPSEEK_API_KEY not found")
        sys.exit(1)

    db = get_db()
    cur = dict_cursor(db)

    # Find stock_analyses rows with missing AI reports
    cur.execute("""
        SELECT sa.id, sa.stock_id, sa.persona, sa.score_composite,
               s.name, s.industry, s.last_price, s.market_cap,
               s.dividend_yield, s.pe_ratio, s.roe, s.debt_to_equity,
               COALESCE(s.financials::text, '{}') as financials_json
        FROM stock_analyses sa
        JOIN stocks s ON sa.stock_id = s.id
        WHERE sa.ai_report IS NULL
          AND sa.score_composite IS NOT NULL
          AND s.status != 'removed'
        ORDER BY sa.score_composite DESC, sa.stock_id
        LIMIT %s
    """, (max_reports,))

    rows = cur.fetchall()
    if not rows:
        print("No missing AI reports — all caught up!")
        cur.close()
        db.close()
        return

    print(f"\nFound {len(rows)} rows needing AI reports")

    generated = 0
    for row in rows:
        code = row["stock_id"]
        name = row["name"]
        persona = row["persona"]
        score = row["score_composite"]

        # Parse financials from JSONB
        fin_data = {}
        try:
            fin_data = json.loads(row["financials_json"]) if isinstance(row["financials_json"], str) else row["financials_json"]
        except (json.JSONDecodeError, TypeError):
            pass
        if not isinstance(fin_data, dict):
            fin_data = {}

        stock_data = {
            "code": code,
            "name": name,
            "industry": row["industry"] or "",
            "last_price": row["last_price"] or 0,
            "market_cap": row["market_cap"] or 0,
            "score_composite": score,
            "financials": fin_data,
        }

        label = f"{name} ({code}) [{persona}] score={score}"
        print(f"  Generating: {label}...", flush=True)

        ai_report = generate_ai_report(stock_data, macro_str, persona)

        if ai_report:
            cur.execute(
                """UPDATE stock_analyses SET ai_report = %s, ai_model = %s,
                   generated_at = NOW() WHERE id = %s""",
                (json.dumps(ai_report), "deepseek-v4-pro", row["id"])
            )
            db.commit()
            generated += 1
            print(f"    ✓ Done ({generated}/{len(rows)})", flush=True)
        else:
            print(f"    ✗ Failed", flush=True)

        # Rate limit: 3 seconds between calls
        time.sleep(1)

    cur.close()
    db.close()

    elapsed = (datetime.now(MYT) - now).total_seconds()
    print(f"\n✓ Generated {generated}/{len(rows)} AI reports")
    print(f"✓ Completed in {elapsed:.0f}s at {datetime.now(MYT).isoformat()}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--max", type=int, default=20, help="Max reports per run")
    args = parser.parse_args()
    main(max_reports=args.max)
