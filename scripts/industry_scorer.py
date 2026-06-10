"""Industry-specific stock scorer v3 — reads from DB, writes score_breakdown properly.

Reads: stocks table (financials JSONB, pe_ratio, roe, dividend_yield, debt_to_equity)
       data/industry_matrix.json (industry factor definitions)
       data/macro_signals.json (macro adjustments — still JSON for now)
Writes: stocks.score_composite, stocks.score_subs, stock_analyses.score_breakdown (proper format)
"""
import json
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(ROOT / "scripts"))
from db import get_db


# ── Load industry matrix ──
MATRIX = json.loads((ROOT / "data" / "industry_matrix.json").read_text())

# ── Load macro signals (still JSON for now — macro_fetcher hasn't been migrated yet) ──
MACRO = {}
macro_path = ROOT / "data" / "macro_signals.json"
if macro_path.exists():
    MACRO = json.loads(macro_path.read_text()).get("signals", {})


def get_financial_from_db(stock_row, factor_name):
    """Map factor name to DB column values."""
    financials = stock_row.get("financials") or []
    latest_q = financials[0] if financials else {}

    def _f(val):
        """Safely convert to float, return None if not a number."""
        if val is None:
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    mapping = {
        "dividend_yield": _f(stock_row.get("dividend_yield")),
        "pe_ratio": _f(stock_row.get("pe_ratio")),
        "roe": _f(stock_row.get("roe")),
        "de_ratio": _f(stock_row.get("debt_to_equity")),
        "revenue_growth_yoy": _f(latest_q.get("revenueGrowthYoY") if latest_q else None),
        "market_cap": _f(stock_row.get("market_cap")),
        "gross_margin": _f(latest_q.get("grossMargin") if latest_q else None),
        "pb_ratio": _f(stock_row.get("pb_ratio")),
    }
    return mapping.get(factor_name)


def get_macro_signal(macro_key):
    s = MACRO.get(macro_key)
    return s["value"] if s else None


def score_factor(factor_name, value, weight, higher_better):
    """Score on 0-100 scale with Bursa-market benchmarks."""
    if value is None:
        return 0

    # Annualize quarterly ROE for proper comparison
    if factor_name == "roe" and value < 15:
        value = value * 4

    benchmarks = {
        "dividend_yield":      [(0,0), (2,10), (4,30), (6,60), (8,80), (12,95), (15,100)],
        "roe":                 [(0,0), (5,20), (8,40), (10,55), (12,70), (15,85), (20,100)],
        "revenue_growth_yoy":  [(-5,0), (0,15), (3,30), (6,45), (10,65), (15,85), (20,100)],
        "gross_margin":        [(0,0), (10,20), (15,40), (20,55), (25,70), (35,85), (45,100)],
        "de_ratio":            [(0,100), (0.3,95), (0.5,85), (1.0,70), (2.0,50), (5.0,30), (10,15), (50,5), (100,0)],
        "pe_ratio":            [(0,100), (6,90), (8,78), (10,70), (12,58), (15,45), (20,30), (25,15), (30,0)],
        "pb_ratio":            [(0,100), (0.5,90), (0.8,78), (1.0,70), (1.5,50), (2.0,30), (3.0,15), (5.0,0)],
    }

    curve = benchmarks.get(factor_name, [(0, 0), (100, 100)])
    if len(curve) < 2:
        return 50

    for i in range(len(curve) - 1):
        x1, y1 = curve[i]
        x2, y2 = curve[i + 1]
        if value >= x1 and value <= x2:
            if x2 == x1:
                return y1
            return y1 + (value - x1) * (y2 - y1) / (x2 - x1)

    if value < curve[0][0]:
        return curve[0][1]
    return curve[-1][1]


def macro_adjustment(industry):
    """Compute macro sensitivity adjustment (-15 to +15)."""
    ind = MATRIX["industries"].get(industry)
    if not ind or "macro_sensitivity" not in ind:
        return 0

    sens = ind["macro_sensitivity"]
    adjustment = 0
    for macro_key, beta in sens.items():
        signal = get_macro_signal(macro_key)
        if signal is None:
            continue
        adjustment += min(abs(beta) * 2, 3) if beta != 0 else 0

    return round(min(max(adjustment, -15), 15), 1)


def score_stock(row):
    """Compute industry-specific composite score from DB row."""
    stock_code = row["id"]
    stock_name = row["name"]
    industry = row.get("industry") or ""

    factors = MATRIX["industries"].get(industry)
    FALLBACK = MATRIX["_fallback"]

    if not factors:
        factors = {"factors": [
            {"name": "dividend_yield", "label": "Dividend Yield", "weight": FALLBACK["dividend"], "higher_better": True},
            {"name": "revenue_growth_yoy", "label": "Revenue Growth YoY", "weight": FALLBACK["growth"], "higher_better": True},
            {"name": "roe", "label": "Return on Equity", "weight": FALLBACK["quality"], "higher_better": True},
            {"name": "de_ratio", "label": "Debt-to-Equity", "weight": FALLBACK["risk"], "higher_better": False},
        ]}

    composite = 0.0
    breakdown = {}

    for f in factors["factors"]:
        value = get_financial_from_db(row, f["name"])
        raw = score_factor(f["name"], value, f["weight"], f["higher_better"])
        weighted = float(raw) * float(f["weight"]) / 100.0
        composite += weighted
        breakdown[f["name"]] = {
            "value": round(value, 2) if value is not None else None,
            "raw": round(raw, 1),
            "weighted": round(weighted, 1),
        }

    macro_adj = macro_adjustment(industry)
    composite += macro_adj
    composite = round(min(max(composite, 0), 100), 1)

    # Map factor names to sub-score categories
    factor_to_sub = {
        "dividend_yield": "dividend",
        "revenue_growth_yoy": "growth",
        "roe": "quality",
        "de_ratio": "risk",
        "gross_margin": "quality",
    }
    subs = {"dividend": 0, "growth": 0, "quality": 0, "risk": 0}
    for fn, b in breakdown.items():
        sub = factor_to_sub.get(fn)
        if sub:
            subs[sub] += round(b["raw"], 1)
    # Cap each sub-score at its max
    subs["dividend"] = min(subs["dividend"], 40)
    subs["growth"] = min(subs["growth"], 30)
    subs["quality"] = min(subs["quality"], 20)
    subs["risk"] = min(subs["risk"], 10)
    subs["composite"] = composite

    return {
        "code": stock_code,
        "name": stock_name,
        "industry": industry,
        "composite": composite,
        "macro_adjustment": macro_adj,
        "breakdown": breakdown,
        "subs": subs,
    }


# ── Score all stocks from DB ──
db = get_db()
cur = db.cursor()

print("=" * 60)
print("Divvy Industry-Specific Stock Scores v3 (DB-driven)")
print("=" * 60)

# Get all active/revisit stocks
cur.execute("""
    SELECT id, name, industry, financials, pe_ratio, roe, dividend_yield,
           debt_to_equity, market_cap
    FROM stocks WHERE status != 'removed' ORDER BY name
""")
columns = [desc[0] for desc in cur.description]
all_rows = [dict(zip(columns, row)) for row in cur.fetchall()]

skipped = 0
results = []
for row in all_rows:
    r = score_stock(row)
    if r["composite"] == 0 and not any(
        get_financial_from_db(row, fn) for fn in ["dividend_yield", "roe", "pe_ratio"]
    ):
        skipped += 1
        continue
    results.append(r)

print(f"Scored {len(results)} stocks, skipped {skipped} (no financial data)")

# Print summary
results.sort(key=lambda x: x["composite"], reverse=True)
print(f"\n{'Stock':10s} {'Composite':>8s} {'Macro':>6s} {'Div':>4s} {'Grw':>4s} {'Qly':>4s} {'Rsk':>4s}")
print("-" * 50)
for r in results[:10]:
    s = r["subs"]
    print(f"{r['code']:10s} {r['composite']:8.1f} {r['macro_adjustment']:+6.1f} "
          f"{s['dividend']:4.0f} {s['growth']:4.0f} {s['quality']:4.0f} {s['risk']:4.0f}")

# Write to DB
PERSONAS = ['ares', 'demeter', 'athena']
inserted = 0
updated = 0

for r in results:
    # Build rationale from score breakdown
    rationale = {
        "sections": {
            "Score Analysis": [
                f"{'🟢' if r['composite'] >= 70 else '🟡' if r['composite'] >= 50 else '🔴'} Composite Score: {r['composite']}/100",
                f"Industry: {r['industry']}",
                *[f"{'✅' if b['raw'] >= 70 else '⚠️' if b['raw'] >= 40 else '❌'} {fn.replace('_', ' ').title()}: {b['raw']:.0f}/100 (weight: {b['weighted']:.0f}%)" 
                  for fn, b in r['breakdown'].items() if b['value'] is not None],
                f"Macro Adjustment: {r['macro_adjustment']:+.1f}",
            ],
            "Action Triggers": [
                {"text": f"Score {r['composite']:.0f}/100 — {'Promote to active' if r['composite'] >= 70 else 'Revisit later'}", "active": r['composite'] >= 70},
                {"text": "Generate AI deep analysis report (decision_rationale populated)", "active": True},
                {"text": "Run Kronos 30-day forecast for price target", "active": True},
            ],
        },
        "sources": {
            "Score Analysis": "Industry matrix + quarterly financials (yfinance via DB)",
            "Action Triggers": "Persona trading rules (persona_config.rules)",
        },
    }
    rationale_json = json.dumps(rationale)

    # Update stocks table
    cur.execute("""
        UPDATE stocks SET
            score_composite = %s,
            score_subs = %s,
            updated_at = NOW()
        WHERE id = %s
    """, (r["composite"], json.dumps(r["subs"]), r["code"]))

    # Update stock_analyses (all 3 personas) — now includes decision_rationale
    for pid in PERSONAS:
        cur.execute("""
            INSERT INTO stock_analyses (stock_id, persona, score_composite, score_breakdown, decision_rationale, generated_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            ON CONFLICT (stock_id, persona) DO UPDATE
            SET score_composite = EXCLUDED.score_composite,
                score_breakdown = EXCLUDED.score_breakdown,
                decision_rationale = EXCLUDED.decision_rationale,
                generated_at = NOW()
        """, (r["code"], pid, r["composite"], json.dumps(r["breakdown"]), rationale_json))
        if cur.rowcount == 1:
            inserted += 1
        else:
            updated += 1

db.commit()
cur.close()
db.close()

print(f"\n✓ Wrote {inserted} new + {updated} updated scores — {len(results)} stocks × 3 personas")

# Top 5 breakdown
print(f"\n{'─'*50}")
print("TOP 5 BREAKDOWN")
print(f"{'─'*50}")
for r in results[:5]:
    print(f"\n{r['code']} ({r['industry']}) — {r['composite']:.1f} (macro: {r['macro_adjustment']:+.1f})")
    for fn, b in r["breakdown"].items():
        v = f"{b['value']:.2f}" if b['value'] is not None else 'N/A'
        print(f"  {fn:22s} v={v:>8} → raw={b['raw']:5.1f} weighted={b['weighted']:5.1f}")
