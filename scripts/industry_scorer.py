"""Industry-specific stock scorer v2 — real data from financial_fetcher + macro_fetcher.

Reads: data/stock_financials.json, data/macro_signals.json, data/industry_matrix.json
Writes: data/stock_scores.json
"""
import json
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent

# ── Load data sources ──
matrix = json.loads((ROOT / "data" / "industry_matrix.json").read_text())
FINANCIALS = {}
fin_path = ROOT / "data" / "stock_financials.json"
if fin_path.exists():
    for name, data in json.loads(fin_path.read_text()).get("stocks", {}).items():
        if "error" not in data:
            FINANCIALS[data["code"]] = data

MACRO = {}
macro_path = ROOT / "data" / "macro_signals.json"
if macro_path.exists():
    MACRO = json.loads(macro_path.read_text()).get("signals", {})

PORTFOLIOS = json.loads((ROOT / "scripts" / "portfolios.json").read_text())

# Map name → code
NAME_TO_CODE = {name: info["code"] for name, info in PORTFOLIOS["stocks"].items()}
CODE_TO_NAME = {v: k for k, v in NAME_TO_CODE.items()}


def get_financial(stock_code, factor_name):
    """Map factor name to real yfinance quarterly data."""
    f = FINANCIALS.get(stock_code, {})

    mapping = {
        "dividend_yield": f.get("dividend_yield_pct"),
        "pe_ratio": f.get("pe_ratio"),
        "pb_ratio": f.get("pb_ratio"),
        "roe": f.get("roe_pct"),  # quarterly ROE — annualize in scoring
        "de_ratio": f.get("de_ratio"),
        "revenue_growth_yoy": f.get("revenue_growth_yoy_pct"),
        "gross_margin": f.get("gross_margin_pct"),
        "market_cap": f.get("market_cap_m"),
    }
    return mapping.get(factor_name)


def get_macro_signal(macro_key):
    """Get macro signal value for industry adjustment."""
    s = MACRO.get(macro_key)
    return s["value"] if s else None


def score_factor(factor_name, value, weight, higher_better):
    """Score on 0-100 scale with Bursa-market benchmarks."""
    if value is None:
        return 0

    # Annualize quarterly ROE for proper comparison
    if factor_name == "roe" and value < 15:
        value = value * 4  # quarterly → annualized

    benchmarks = {
        # Higher is better (value, score) pairs
        "dividend_yield":      [(0,0), (2,10), (4,30), (6,60), (8,80), (12,95), (15,100)],
        "roe":                 [(0,0), (5,20), (8,40), (10,55), (12,70), (15,85), (20,100)],
        "revenue_growth_yoy":  [(-5,0), (0,15), (3,30), (6,45), (10,65), (15,85), (20,100)],
        "gross_margin":        [(0,0), (10,20), (15,40), (20,55), (25,70), (35,85), (45,100)],
        "order_book":          [(0,0), (100,20), (500,40), (1000,60), (2000,80), (5000,100)],
        "casa_ratio":          [(0,0), (15,20), (20,40), (25,55), (30,75), (35,90), (40,100)],
        "loan_growth_yoy":     [(-3,0), (0,15), (3,30), (5,50), (8,70), (10,85), (15,100)],
        "nim":                 [(0,0), (1.5,20), (2.0,40), (2.2,55), (2.5,75), (2.8,90), (3.5,100)],
        "car":                 [(8,0), (10,20), (12,45), (14,65), (16,80), (18,95), (20,100)],
        "occupancy":           [(50,0), (70,30), (80,50), (85,65), (90,78), (95,90), (98,100)],
        "npi_yield":           [(0,0), (3,20), (4,40), (5,60), (6,75), (7,90), (8,100)],
        "wale":                [(0,0), (1,15), (2,35), (3,55), (4,75), (5,90), (7,100)],
        "property_diversity":  [(0,0), (1,20), (2,50), (3,75), (4,100)],
        "export_pct":          [(0,0), (20,15), (40,35), (60,55), (80,78), (90,90), (95,100)],
        "portfolio_quality":   [(0,0), (30,25), (50,50), (70,75), (90,100)],
        "capacity_growth":     [(0,0), (2,15), (4,30), (6,50), (8,75), (10,90), (15,100)],
        "capital_allocation":  [(0,0), (25,20), (50,45), (70,70), (85,90), (100,100)],
        "regulated_return":    [(0,0), (5,25), (7,50), (8,70), (9,85), (10,100)],
        "ffb_yield":           [(0,0), (10,20), (15,40), (20,60), (25,80), (30,100)],

        # Lower is better (inverted benchmarks)
        "de_ratio":            [(0,100), (0.3,95), (0.5,85), (1.0,70), (2.0,50), (5.0,30), (10,15), (50,5), (100,0)],
        "pe_ratio":            [(0,100), (6,90), (8,78), (10,70), (12,58), (15,45), (20,30), (25,15), (30,0)],
        "pb_ratio":            [(0,100), (0.5,90), (0.8,78), (1.0,70), (1.5,50), (2.0,30), (3.0,15), (5.0,0)],
        "npl_ratio":           [(0,100), (1,95), (2,80), (3,65), (4,45), (5,25), (7,10), (10,0)],
        "cost_income":         [(20,100), (30,90), (40,78), (45,65), (50,50), (55,30), (60,15), (70,0)],
        "gearing":             [(0,100), (20,95), (30,80), (35,65), (40,45), (45,25), (50,10), (60,0)],
        "production_cost":     [(0,100), (1500,90), (1800,75), (2000,65), (2200,50), (2500,25), (2800,0)],
        "customer_conc":       [(0,100), (20,90), (30,78), (40,65), (50,50), (65,25), (80,0)],
        "nav_discount":        [(0,100), (10,95), (20,85), (30,70), (40,50), (50,25), (60,10), (70,0)],
        "sop_discount":        [(0,100), (10,90), (20,78), (30,65), (40,50), (50,25), (60,10), (70,0)],
    }

    curve = benchmarks.get(factor_name, [(0, 0), (100, 100)])
    if len(curve) < 2:
        return 50

    # Linear interpolation along benchmark curve
    for i in range(len(curve) - 1):
        x1, y1 = curve[i]
        x2, y2 = curve[i + 1]
        if value >= x1 and value <= x2:
            if x2 == x1:
                return y1
            return y1 + (value - x1) * (y2 - y1) / (x2 - x1)

    # Outside range — clamp
    if value < curve[0][0]:
        return curve[0][1]
    return curve[-1][1]


def macro_adjustment(industry, stock_code):
    """Compute macro sensitivity adjustment (-15 to +15)."""
    ind = matrix["industries"].get(industry)
    if not ind or "macro_sensitivity" not in ind:
        return 0

    sens = ind["macro_sensitivity"]
    adjustment = 0
    for macro_key, beta in sens.items():
        signal = get_macro_signal(macro_key)
        if signal is None:
            continue
        # Simple: trend direction × beta × scale
        # For now we don't have trend for all — use value presence as +1 bias
        adjustment += min(abs(beta) * 2, 3) if beta != 0 else 0

    return round(min(max(adjustment, -15), 15), 1)


def score_stock(stock_code, stock_name, industry):
    """Compute industry-specific composite score."""
    factors = matrix["industries"].get(industry)
    FALLBACK = matrix["_fallback"]

    if not factors:
        factors = {"factors": [
            {"name": "dividend_yield", "label": "Dividend Yield", "weight": FALLBACK["dividend"], "higher_better": True},
            {"name": "revenue_growth_yoy", "label": "Revenue Growth YoY", "weight": FALLBACK["growth"], "higher_better": True},
            {"name": "roe", "label": "Return on Equity", "weight": FALLBACK["quality"], "higher_better": True},
            {"name": "de_ratio", "label": "Debt-to-Equity", "weight": FALLBACK["risk"], "higher_better": False},
        ]}

    composite = 0
    breakdown = {}

    for f in factors["factors"]:
        value = get_financial(stock_code, f["name"])
        raw = score_factor(f["name"], value, f["weight"], f["higher_better"])
        weighted = raw * f["weight"] / 100
        composite += weighted
        breakdown[f["name"]] = {
            "value": round(value, 2) if value is not None else None,
            "raw": round(raw, 1),
            "weighted": round(weighted, 1),
        }

    macro_adj = macro_adjustment(industry, stock_code)
    composite += macro_adj

    return {
        "code": stock_code,
        "name": stock_name,
        "industry": industry,
        "composite": round(min(max(composite, 0), 100), 1),
        "macro_adjustment": macro_adj,
        "breakdown": breakdown,
    }


# ── Score all ──
print("=" * 60)
print("Divvy Industry-Specific Stock Scores v2 (yfinance data)")
print("=" * 60)

# Old scores for comparison
OLD_SCORES = {}
for code, old in [
    ("1155.KL", 72), ("5106.KL", 68), ("6742.KL", 65), ("3379.KL", 60),
    ("7089.KL", 62), ("4731.KL", 66), ("0104.KL", 55), ("2445.KL", 70),
    ("0166.KL", 58), ("4197.KL", 64), ("7087.KL", 93), ("5983.KL", 92),
    ("5293.KL", 77), ("5132.KL", 72), ("5142.KL", 69), ("5280.KL", 67),
    ("INTA.KL", 65),
]:
    OLD_SCORES[code] = old

results = []
for name, info in PORTFOLIOS["stocks"].items():
    if "kronos_warning" in info:
        continue  # skip flagged stocks
    r = score_stock(info["code"], info["name"], info.get("industry", ""))
    results.append(r)

results.sort(key=lambda x: x["composite"], reverse=True)

print(f"\n{'Stock':10s} {'Industry':20s} {'New':>6s} {'Old':>6s} {'Macro':>6s} {'Δ':>6s}")
print("-" * 65)
for r in results:
    old = OLD_SCORES.get(r["code"], 0)
    delta = r["composite"] - old
    d = f"+{delta:.0f}" if delta > 0 else f"{delta:.0f}"
    m = f"+{r['macro_adjustment']:.0f}" if r['macro_adjustment'] > 0 else f"{r['macro_adjustment']:.0f}"
    name = CODE_TO_NAME.get(r["code"], r["code"])
    print(f"{name:10s} {r['industry']:20s} {r['composite']:6.1f} {old:6d} {m:>6s} {d:>6s}")

# Save
output = {
    "date": datetime.now().strftime("%Y-%m-%d"),
    "macro_date": MACRO.get("date") if MACRO else None,
    "scores": results,
}
(ROOT / "data" / "stock_scores.json").write_text(json.dumps(output, indent=2))
print(f"\n✓ Saved to data/stock_scores.json — {len(results)} stocks")

# Top 5 breakdown
print(f"\n{'─'*50}")
print("TOP 5 BREAKDOWN")
print(f"{'─'*50}")
for r in results[:5]:
    print(f"\n{r['code']} ({r['industry']}) — {r['composite']:.1f} (macro: {r['macro_adjustment']:+.1f})")
    for fn, b in r["breakdown"].items():
        v = f"{b['value']:.2f}" if b['value'] is not None else 'N/A'
        print(f"  {fn:22s} v={v:>8} → raw={b['raw']:5.1f} weighted={b['weighted']:5.1f}")
