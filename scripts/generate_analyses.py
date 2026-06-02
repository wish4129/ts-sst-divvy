"""Generate and store deep analysis for every persona holding."""
import sys, json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from db import get_db, dict_cursor

MYT = timezone(timedelta(hours=8))

# ── Load data ──
pf = json.loads((ROOT / "scripts" / "portfolios.json").read_text())
scores = json.loads((ROOT / "data" / "stock_scores.json").read_text())
macro = json.loads((ROOT / "data" / "macro_signals.json").read_text())
kronos = {}
if (ROOT / "data" / "kronos_forecast.json").exists():
    kronos = json.loads((ROOT / "data" / "kronos_forecast.json").read_text())

# ── Persona strategies ──
STRATEGIES = {
    "ares": "Aggressive momentum + deep value. Strike fast, cut losers at -12%. "
            "Kronos-driven momentum cooling. High conviction, high turnover. "
            "Max 25% single bet. You hold this because it has strong momentum "
            "or deep value characteristics within Ares's risk tolerance.",
    "demeter": "Conservative dividend compounder. Steady harvest, 10% cash buffer. "
               "Trim if yield drops below 3%. You hold this because it provides "
               "reliable dividend income with low downside risk.",
    "athena": "Hybrid GARP (Growth at Reasonable Price). Sell 50% at +25%, "
              "full exit at +40%. Dip buy at -10%. Tactical rotation. "
              "You hold this because it balances growth potential with reasonable valuation.",
}

def build_rationale(pid, stock_name, stock_info, holding, score_data, ksig):
    """Generate decision rationale for a persona holding."""
    target = holding.get('target_pct', 0)
    shares = holding.get('shares', 0)
    cost = holding.get('cost', 0)
    
    parts = []
    
    # Persona context
    if pid == "ares":
        if ksig and ksig.get('pred_change_pct', 0) > 5:
            parts.append(f"Kronos bullish {ksig['pred_change_pct']:+.1f}% — strong momentum signal")
        elif ksig and ksig.get('pred_change_pct', 0) < -5:
            parts.append(f"Kronos bearish {ksig['pred_change_pct']:+.1f}% — monitoring for momentum cooling trigger")
        parts.append(f"{target}% allocation — fits within 25% max single position rule")
        
    elif pid == "demeter":
        dy = score_data.get('breakdown', {}).get('dividend_yield', {}).get('value')
        if dy and dy > 4:
            parts.append(f"Dividend yield {dy:.1f}% — above Demeter's 3% floor")
        if stock_info.get('industry') == 'REIT':
            parts.append("REIT holding provides inflation-hedged income")
        parts.append(f"{target}% allocation — diversified across {len(pf['personas'][pid]['holdings'])} positions")
        
    elif pid == "athena":
        roe = score_data.get('breakdown', {}).get('roe', {}).get('value')
        pe = score_data.get('breakdown', {}).get('pe_ratio', {}).get('value')
        if roe and roe > 15:
            parts.append(f"ROE {roe:.1f}% — strong profitability for GARP")
        if pe and pe < 15:
            parts.append(f"P/E {pe:.1f}x — attractive valuation")
        parts.append(f"{target}% allocation — tactical position for rotation")
    
    # Score context
    comp = score_data.get('composite', 0)
    if comp >= 70:
        parts.append(f"Composite score {comp:.0f}/100 — top-tier fundamentals")
    elif comp >= 50:
        parts.append(f"Composite score {comp:.0f}/100 — solid fundamentals")
    
    # Macro context
    macro_adj = score_data.get('macro_adjustment', 0)
    if macro_adj > 2:
        parts.append(f"Macro tailwind +{macro_adj:.0f} — favorable market regime")
    elif macro_adj < -2:
        parts.append(f"Macro headwind {macro_adj:.0f}")
    
    # Kronos context
    if ksig and 'pred_change_pct' in ksig:
        pct = ksig['pred_change_pct']
        if pct > 10:
            parts.append(f"Kronos forecasts +{pct:.1f}% in 30 days")
        elif pct < -10:
            parts.append(f"⚠️ Kronos warns {pct:.1f}% — review stop loss")
    
    return " | ".join(parts) if parts else "Hold based on portfolio strategy allocation."


# ── Generate and store ──
db = get_db()
cur = dict_cursor(db)

generated = 0
for pid in ["ares", "demeter", "athena"]:
    persona = pf["personas"][pid]
    for name, holding in persona["holdings"].items():
        info = pf["stocks"].get(name, {})
        code = info.get("code", name)
        
        # Find score data
        score_data = next((s for s in scores["scores"] if s["code"] == code), {})
        
        # Kronos signal
        ksig = kronos.get(name, {})
        
        # Build rationale
        rationale = build_rationale(pid, name, info, holding, score_data, ksig)
        
        # Macro context for this stock
        ind_macro = {}
        for mk, mv in macro.get("signals", {}).items():
            ind_macro[mk] = {
                "label": mv.get("label", mk),
                "value": mv.get("value"),
                "trend": mv.get("trend"),
            }
        
        cur.execute(
            """INSERT INTO stock_analyses (stock_id, persona, score_composite, score_breakdown,
               decision_rationale, kronos_signal, macro_context)
               VALUES (%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (stock_id, persona) 
               DO UPDATE SET score_composite=EXCLUDED.score_composite,
                             score_breakdown=EXCLUDED.score_breakdown,
                             decision_rationale=EXCLUDED.decision_rationale,
                             kronos_signal=EXCLUDED.kronos_signal,
                             macro_context=EXCLUDED.macro_context,
                             generated_at=now()""",
            (code, pid, score_data.get("composite"),
             json.dumps(score_data.get("breakdown", {})),
             rationale,
             json.dumps(ksig) if ksig else None,
             json.dumps(ind_macro))
        )
        generated += 1
        print(f"  {pid:8s} {name:10s} ({code}) — {score_data.get('composite', 0):.0f}")

db.commit()
cur.close()
db.close()
print(f"\n✓ Generated {generated} analyses")
