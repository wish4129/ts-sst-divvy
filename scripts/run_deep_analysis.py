#!/usr/bin/env python3
"""Deep Analysis Generator — rerun weekly to update persona rationales.

Reads: portfolios.json, stock_scores.json, macro_signals.json, kronos_forecast.json, stocks table
Writes: stock_analyses table (keeps history — no UNIQUE constraint)

Two-phase analysis:
  1. Portfolio holdings — full rationale with structured sections + AI report
  2. Watchlist stocks — AI report only (stocks in DB not in any persona portfolio)

AI reports use markdown-based section parsing (## headers) — more reliable than JSON.
Retries up to 2 times on failure. PYTHONUNBUFFERED=1 recommended for cron runs."""
import sys
# Force unbuffered output for cron runs
sys.stdout.reconfigure(line_buffering=True)
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from db import get_db, dict_cursor

MYT = timezone(timedelta(hours=8))

# ── Load all data ──
pf = json.loads((ROOT / "scripts" / "portfolios.json").read_text())
scores = json.loads((ROOT / "data" / "stock_scores.json").read_text())
macro = json.loads((ROOT / "data" / "macro_signals.json").read_text())
kronos = json.loads((ROOT / "data" / "kronos_forecast.json").read_text()) if (ROOT / "data" / "kronos_forecast.json").exists() else {}
fin = json.loads((ROOT / "data" / "stock_financials.json").read_text())

# Index scores by code
score_by_code = {s["code"]: s for s in scores["scores"]}
fin_by_code = {}
for name, data in fin.get("stocks", {}).items():
    if "error" not in data:
        fin_by_code[data["code"]] = data

# ── Persona strategy context for rationale ──
PERSONA_CONTEXT = {
    "ares": {
        "name": "Ares — God of War",
        "style": "Aggressive Momentum + Deep Value",
        "philosophy": "Strike fast. Momentum-driven entries, cut losers ruthlessly at -12%. "
                      "No take-profit — let compounders run. Max 25% single bet. "
                      "High conviction, high turnover. Kronos signals override fundamentals "
                      "when momentum is strong.",
        "triggers": [
            "Kronos bearish ≥7 strength → trim 15%",
            "Momentum cooling (-5% intraday) → trim 25%",
            "Stop loss -12% → full exit",
        ],
        "sizing": "4-6 positions, max 25% single bet, rebalance at 7% drift",
    },
    "demeter": {
        "name": "Demeter — Harvest Goddess",
        "style": "Conservative Dividend Compound",
        "philosophy": "Steady harvest. Dividend compounding is the primary return driver. "
                      "10% cash buffer earning FD 3% p.a. Only trim if dividend yield "
                      "drops below 3% (price ran too far from yield). Dividend cut >20% "
                      "triggers review. Tight 10% rebalance band.",
        "triggers": [
            "Dividend yield <3% → DY compression trim",
            "Dividend cut >20% → review for exit",
            "Excess cash >15% → deploy to highest-scored underweight",
        ],
        "sizing": "5-7 positions, max 35% single bet, 10% cash buffer, rebalance at 10% drift",
    },
    "athena": {
        "name": "Athena — Goddess of Wisdom",
        "style": "Hybrid GARP (Growth at Reasonable Price)",
        "philosophy": "Tactical GARP. Balance growth potential with valuation discipline. "
                      "Sell 50% at +25% gain, full exit at +40%. Buy 50% more on dips "
                      "below -10% (once per 30 days max). Rotate between defensive and "
                      "cyclical based on macro regime. Max 30% single bet.",
        "triggers": [
            "Take profit +25% → sell 50%",
            "Full exit +40% → sell all",
            "Dip buy -10% → buy 50% more (30d cooldown)",
            "Stop loss -10% → full exit",
        ],
        "sizing": "5-6 positions, max 30% single bet, rebalance at 10% drift",
    },
}


def build_detailed_rationale(pid, stock_name, stock_info, holding, score_data, fin_data, ksig, macro_signals):
    """Build comprehensive multi-section rationale for a persona holding."""
    ctx = PERSONA_CONTEXT[pid]
    code = stock_info["code"]
    target = holding.get("target_pct", 0)
    shares = holding.get("shares", 0)
    cost = holding.get("cost", 0)
    industry = stock_info.get("industry", "")
    comp = score_data.get("composite", 0)

    sections = {}

    # ── 1. Strategic Fit ──
    fit_parts = []
    if pid == "ares":
        if ksig and "pred_change_pct" in ksig:
            pct = ksig["pred_change_pct"]
            if pct > 10:
                fit_parts.append(f"Strong momentum signal: Kronos +{pct:.1f}% in 30 days — aligns with Ares's momentum-first strategy")
            elif pct > 0:
                fit_parts.append(f"Positive Kronos signal +{pct:.1f}% supports momentum thesis")
            else:
                fit_parts.append(f"Kronos {pct:+.1f}% — monitoring closely for momentum cooling trigger at -5%")
        dy = fin_data.get("dividend_yield_pct")
        if dy and dy > 5:
            fit_parts.append(f"Dividend yield {dy:.1f}% provides downside cushion during momentum corrections")
    elif pid == "demeter":
        dy = fin_data.get("dividend_yield_pct")
        if dy and dy > 5:
            fit_parts.append(f"Dividend yield {dy:.1f}% — comfortably above Demeter's 3% floor, compounds steadily")
        elif dy:
            fit_parts.append(f"Dividend yield {dy:.1f}% — meets minimum threshold, monitor for yield compression")
        de = fin_data.get("de_ratio")
        if de is not None and de < 1:
            fit_parts.append(f"Low leverage (D/E {de:.2f}) — conservative capital structure aligns with Demeter's risk profile")
    elif pid == "athena":
        pe = fin_data.get("pe_ratio")
        roe = fin_data.get("roe_pct")
        if pe and pe < 12:
            fit_parts.append(f"P/E {pe:.1f}x — attractive valuation for GARP entry")
        if roe:
            roe_annual = roe * 4 if roe < 15 else roe
            if roe_annual > 12:
                fit_parts.append(f"ROE {roe_annual:.1f}% annualized — strong profitability supports growth thesis")
    
    fit_parts.append(f"{target}% portfolio allocation within {ctx['sizing'].split(',')[0]}")
    sections["Strategic Fit"] = fit_parts

    # ── 2. Score Analysis ──
    score_parts = []
    score_parts.append(f"Industry-specific composite: {comp:.0f}/100")
    macro_adj = score_data.get("macro_adjustment", 0)
    if macro_adj != 0:
        score_parts.append(f"Macro adjustment: {macro_adj:+.0f} points — {_macro_narrative(macro_adj)}")
    
    breakdown = score_data.get("breakdown", {})
    top_factors = sorted(breakdown.items(), key=lambda x: x[1].get("weighted", 0), reverse=True)[:3]
    for fn, b in top_factors:
        v = b.get("value")
        if v is not None:
            score_parts.append(f"{fn.replace('_', ' ')}: {v} → {b['weighted']:.1f} weighted")
    sections["Score Analysis"] = score_parts

    # ── 3. Kronos AI Signal ──
    if ksig and "pred_change_pct" in ksig:
        pct = ksig["pred_change_pct"]
        direction = "Bullish ▲" if pct > 5 else "Bearish ▼" if pct < -5 else "Neutral —"
        kronos_parts = [
            f"{direction} 30-day forecast: {pct:+.1f}%",
            f"Predicted range: RM{ksig.get('pred_low', 0):.2f} – RM{ksig.get('pred_high', 0):.2f}",
            f"Volatility: {ksig.get('pred_volatility', 0):.1f}%",
        ]
        if "error" not in ksig:
            sections["Kronos AI 30-Day Forecast"] = kronos_parts
    else:
        sections["Kronos AI 30-Day Forecast"] = ["No forecast available for this stock"]

    # ── 4. Macro Context ──
    ind_matrix = json.loads((ROOT / "data" / "industry_matrix.json").read_text())
    ind_sens = ind_matrix.get("industries", {}).get(industry, {}).get("macro_sensitivity", {})
    macro_parts = []
    for mk, mv in macro_signals.items():
        beta = ind_sens.get(mk, 0)
        if abs(beta) > 0.3 and mv.get("value") is not None:
            impact = "tailwind" if (beta > 0 and mv.get("trend") == "up") or (beta < 0 and mv.get("trend") == "down") else "headwind"
            macro_parts.append(f"{mv['label']}: {mv['value']} ({mv.get('trend','?')}) — {impact} (beta={beta})")
    sections["Macro Context"] = macro_parts[:5] if macro_parts else ["No significant macro exposure"]

    # ── 5. Risk Factors ──
    risks = []
    de = fin_data.get("de_ratio")
    if de is not None and de > 2:
        risks.append(f"Elevated leverage D/E {de:.1f}x — rate sensitivity risk")
    if ksig and ksig.get("pred_change_pct", 0) < -10:
        risks.append(f"Kronos warns {ksig['pred_change_pct']:.1f}% — significant downside risk")
    if fin_data.get("revenue_growth_yoy_pct") is not None and fin_data["revenue_growth_yoy_pct"] < 0:
        risks.append(f"Revenue declining {fin_data['revenue_growth_yoy_pct']:.1f}% YoY")
    sections["Risk Factors"] = risks if risks else ["No significant risk flags identified"]

    # ── 6. Action Triggers — structured with active state ──
    triggers = []
    trig_sources = {
        "ares": "https://github.com/wish4129/ts-sst-divvy/blob/main/scripts/portfolios.json",
        "demeter": "https://github.com/wish4129/ts-sst-divvy/blob/main/scripts/portfolios.json",
        "athena": "https://github.com/wish4129/ts-sst-divvy/blob/main/scripts/portfolios.json",
    }
    for t in ctx["triggers"]:
        triggers.append({"text": t, "active": False, "source_url": trig_sources.get(pid, "")})
    
    # Dynamic active triggers
    if pid == "ares" and ksig and ksig.get("pred_change_pct", 0) < -10:
        triggers.append({"text": "⚠️ Kronos bearish beyond threshold — next run may trigger trim", "active": True, "source_url": trig_sources.get(pid, "")})
    if pid == "demeter" and fin_data.get("dividend_yield_pct", 0) < 4:
        triggers.append({"text": "⚠️ Dividend yield approaching 3% floor — monitor", "active": True, "source_url": trig_sources.get(pid, "")})
    if pid == "athena":
        pe = fin_data.get("pe_ratio")
        if pe and pe > 20:
            triggers.append({"text": "⚠️ P/E above GARP threshold — watch for take-profit signal", "active": True, "source_url": trig_sources.get(pid, "")})
    sections["Action Triggers"] = triggers

    # ── 7. Source References ──
    sources = {
        "Quarterly Financials": "https://finance.yahoo.com/quote/" + code,
        "Industry Matrix": "https://github.com/wish4129/ts-sst-divvy/blob/main/data/industry_matrix.json",
        "Macro Signals": "https://github.com/wish4129/ts-sst-divvy/blob/main/data/macro_signals.json",
        "Kronos Model": "https://huggingface.co/NeoQuasar/Kronos-small",
        "Portfolio Strategy": trig_sources.get(pid, ""),
        "Stock Scores": "https://github.com/wish4129/ts-sst-divvy/blob/main/data/stock_scores.json",
    }

    return {"sections": sections, "sources": sources}


def generate_ai_report(stock_name, stock_info, fin_data, score_data, ksig, macro_signals, persona, pf_stocks, max_retries=2):
    """Call DeepSeek v4 Pro to produce a comprehensive AI analysis report.
    
    Uses markdown-based section parsing (more reliable than JSON). Retries on failure.
    """
    import os, re, time
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        # Fallback: read from ~/.hermes/.env
        env_file = Path.home() / ".hermes" / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if "DEEPSEEK_API_KEY" in line and not line.startswith("#"):
                    api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    if not api_key:
        return None
    
    code = stock_info["code"]
    industry = stock_info.get("industry", "")
    
    # Build context
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
        for v in list(macro_signals.values())[:5]
    ) if macro_signals else "No macro data"
    
    score_comp = score_data.get("composite", "N/A")
    score_macro = score_data.get("macro_adjustment", 0)
    
    prompt = f"""You are a Bursa Malaysia analyst for the {persona.upper()} persona ({PERSONA_CONTEXT[persona]['style']}).

Write a concise analysis with EXACTLY these ## markdown headers:

## Introduction & History
## Trend Analysis
## Strengths
## Weaknesses
## Summary
## Target

STOCK: {stock_name} ({code}) — {industry}
Price: RM{price_now} | MCap: RM{mcap}M | P/E: {pe}x | DY: {dy}% | ROE: {roe}% | D/E: {de}
Rev Growth: {rev_growth}% | Score: {score_comp}/100 (Macro Adj: {score_macro:+})
Kronos 30d: {kronos_pct}% (RM{kronos_low}–RM{kronos_high}, vol {kronos_vol}%)
Macro: {macro_summary}

For Strengths/Weaknesses: use "- " bullet points.
For Target: include price target (RM), cut loss (RM), timeframe, volatility, hidden risks.
Use Malaysian English. Be specific with the numbers provided."""

    SECTION_MAP = {
        "introduction": "introduction_history", "history": "introduction_history",
        "trend": "trend_analysis", "strength": "strengths", "weakness": "weaknesses",
        "summary": "summary", "target": "target",
    }

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
            
            # Parse markdown sections
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
                lower_h = header.lower()
                for keyword, key in SECTION_MAP.items():
                    if keyword in lower_h:
                        sections[key] = text
                        break
            
            required = ["introduction_history", "trend_analysis", "strengths", "weaknesses", "summary"]
            if all(k in sections for k in required):
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
            
            if attempt < max_retries:
                time.sleep(2)
                continue
            return None
            
        except Exception as e:
            if attempt < max_retries:
                time.sleep(2)
                continue
            print(f"  ⚠ AI report failed for {stock_name} after {max_retries+1} attempts: {e}", flush=True)
            return None
    
    return None


def _macro_narrative(adj):
    if adj > 3: return "favorable macro regime boosting scores"
    if adj > 0: return "modest macro support"
    if adj < -3: return "macro headwinds pressuring scores"
    if adj < 0: return "slight macro drag"
    return "neutral macro environment"


# ── Generate and store ──
db = get_db()
cur = dict_cursor(db)
now = datetime.now(MYT)

generated = 0
generated_ai = 0

# 1. Portfolio holdings (existing logic)
for pid in ["ares", "demeter", "athena"]:
    persona = pf["personas"][pid]
    for name, holding in persona["holdings"].items():
        info = pf["stocks"].get(name, {})
        if not info:
            continue
        code = info["code"]
        
        score_data = score_by_code.get(code, {})
        fin_data = fin_by_code.get(code, {})
        ksig = kronos.get(name, {})
        
        result = build_detailed_rationale(
            pid, name, info, holding, score_data, fin_data, ksig,
            macro.get("signals", {})
        )
        
        # Generate AI report via DeepSeek (markdown parser, with retries)
        ai_report = generate_ai_report(
            name, info, fin_data, score_data, ksig,
            macro.get("signals", {}), pid, pf["stocks"]
        )
        
        cur.execute(
            """INSERT INTO stock_analyses (stock_id, persona, score_composite, score_breakdown,
               decision_rationale, kronos_signal, macro_context, ai_report, ai_model)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (code, pid, score_data.get("composite"),
             json.dumps(score_data.get("breakdown", {})),
             json.dumps(result),
             json.dumps(ksig) if ksig else None,
             json.dumps(macro.get("signals", {})),
             json.dumps(ai_report) if ai_report else None,
             "deepseek-v4-pro" if ai_report else None)
        )
        generated += 1
        if ai_report:
            generated_ai += 1
            print(f"  {pid:8s} {name:10s} ({code}) — ✓ AI report", flush=True)
        else:
            print(f"  {pid:8s} {name:10s} ({code}) — rationale only", flush=True)

# 2. Watchlist stocks (from DB stocks table, excluding portfolio holdings)
portfolio_codes = set()
for pid in ["ares", "demeter", "athena"]:
    for name, holding in pf["personas"][pid]["holdings"].items():
        info = pf["stocks"].get(name, {})
        if info.get("code"):
            portfolio_codes.add(info["code"])

cur.execute("SELECT id, name, industry, initial_price FROM stocks WHERE status != 'removed'")
watchlist = [(r["id"], r["name"], r.get("industry", ""), float(r.get("initial_price", 0) or 0)) 
             for r in cur.fetchall() if r["id"] not in portfolio_codes]

if watchlist:
    print(f"\n── Watchlist ({len(watchlist)} stocks) ──")
    
    for code, name, industry, price in watchlist:
        # Build minimal stock_info and fin_data for watchlist stocks
        stock_info = {"code": code, "industry": industry}
        fin_data = fin_by_code.get(code, {})
        score_data = score_by_code.get(code, {"composite": 50, "breakdown": {}})
        ksig = kronos.get(name, {})
        
        for pid in ["ares", "demeter", "athena"]:
            ai_report = generate_ai_report(
                name, stock_info, fin_data, score_data, ksig,
                macro.get("signals", {}), pid, pf["stocks"]
            )
            
            if ai_report:
                cur.execute(
                    """INSERT INTO stock_analyses (stock_id, persona, score_composite, score_breakdown,
                       decision_rationale, kronos_signal, macro_context, ai_report, ai_model)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (code, pid, score_data.get("composite"),
                     json.dumps(score_data.get("breakdown", {})),
                     json.dumps({"sections": {}, "sources": {}}),
                     json.dumps(ksig) if ksig else None,
                     json.dumps(macro.get("signals", {})),
                     json.dumps(ai_report), "deepseek-v4-pro")
                )
                generated += 1
                generated_ai += 1
                print(f"  {pid:8s} {name:20s} ({code}) — ✓ AI report", flush=True)

db.commit()
cur.close()
db.close()
print(f"\n✓ Generated {generated} analyses ({generated_ai} with AI reports) at {now.isoformat()}")
