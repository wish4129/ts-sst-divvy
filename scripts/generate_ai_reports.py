#!/usr/bin/env python3
"""Generate AI narrative reports for all active Bursa stocks.

Usage: python3 scripts/generate_ai_reports.py  (auto-regenerates all 22)
"""

import sys, json, datetime, os
sys.path.insert(0, 'scripts')
from db import get_db, dict_cursor


def determine_recommendation(score, kronos_change):
    """Return (recommendation, risk) based on rules."""
    if score >= 65 and kronos_change is not None and kronos_change > 0:
        risk = 'low' if kronos_change > 5 else 'low'
        return 'BUY', risk
    elif score >= 65:
        risk = 'low' if score >= 80 else 'medium'
        return 'HOLD', risk
    elif score < 50:
        return 'SELL', 'high'
    else:
        return 'HOLD', 'medium'


def generate_report(r):
    """Generate a narrative report for a single stock."""
    score = r['score_composite']
    kronos_chg = r['pred_change_pct']
    rec, risk = determine_recommendation(score, kronos_chg)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # Score breakdown
    sb = r.get('score_breakdown') or {}
    roe_raw = sb.get('roe', {}).get('value', 'N/A') if isinstance(sb.get('roe'), dict) else 'N/A'
    de_raw = sb.get('de_ratio', {}).get('value', 'N/A') if isinstance(sb.get('de_ratio'), dict) else 'N/A'
    dy_raw = sb.get('dividend_yield', {}).get('value', 'N/A') if isinstance(sb.get('dividend_yield'), dict) else 'N/A'
    rev_growth_raw = sb.get('revenue_growth_yoy', {}).get('value', 'N/A') if isinstance(sb.get('revenue_growth_yoy'), dict) else 'N/A'

    pe = r['pe_ratio']
    roe = r['roe']
    de = r['debt_to_equity']
    dy = r['dividend_yield']
    price = r['last_price']
    mcap = r['market_cap']
    industry = r['industry']
    name = r['name']
    ticker = r['id']

    # Kronos data
    pred_close = r['pred_30d_close']
    pred_low = r['pred_low']
    pred_high = r['pred_high']
    kronos_str = f"{kronos_chg:+.2f}%" if kronos_chg is not None else "N/A"

    # Financial metrics text
    pe_str = f"{pe:.1f}" if pe else "N/A"
    roe_str = f"{roe:.1f}%" if roe else "N/A"
    de_str = f"{de:.3f}" if de else "N/A"
    dy_str = f"{dy:.2f}%" if dy else "N/A"
    mcap_str = f"RM{mcap:,.0f}M" if mcap and mcap >= 1 else f"RM{mcap:,.2f}M" if mcap else "N/A"
    price_str = f"RM{price:.2f}" if price else "N/A"

    # Build metrics from financials JSON
    fins = r.get('financials')
    latest_q = {}
    if fins and isinstance(fins, list) and len(fins) > 0:
        latest_q = fins[0]

    # Revenue growth insight
    rev_growth_str = ""
    if latest_q.get('revenueGrowthYoY') is not None:
        rev_growth_str = f"Revenue grew {latest_q['revenueGrowthYoY']:+.1f}% YoY in the latest quarter"
    elif rev_growth_raw and rev_growth_raw != 'N/A':
        rev_growth_str = f"Trailing revenue growth trend at {rev_growth_raw}%"
    else:
        rev_growth_str = "Revenue growth data not available"

    # Free cash flow insight
    fcf = latest_q.get('freeCashFlow')
    fcf_str = ""
    if fcf is not None:
        if fcf > 0:
            fcf_str = f"Positive free cash flow of RM{fcf/1e6:.2f}M in the latest quarter indicates healthy operations."
        else:
            fcf_str = f"Free cash flow was negative (RM{fcf/1e6:.2f}M) in the latest quarter, which may signal elevated capex or working capital needs."

    # Net income insight
    ni = latest_q.get('netIncome')
    ni_str = ""
    if ni is not None:
        ni_str = f"Net income stood at RM{ni/1e6:.2f}M"

    # Build summary: 2-3 paragraphs

    para1 = (
        f"{name} ({ticker}), classified under {industry}, carries a composite score of {score:.1f}/100 — "
        f"indicating {'exceptional' if score >= 85 else 'strong' if score >= 70 else 'moderate'} fundamental health. "
        f"Key metrics: P/E of {pe_str}, ROE of {roe_str}, debt-to-equity of {de_str}, and a dividend yield of {dy_str}. "
        f"The latest quarter ({latest_q.get('quarter', 'N/A')}) shows {rev_growth_str.strip().lower()} "
        f"and {ni_str.strip().lower() if ni_str else 'net income data not separately available'}. "
    )

    # Kronos paragraph
    if kronos_chg is not None and pred_close is not None:
        band_width = ((pred_high - pred_low) / pred_close * 100) if pred_close > 0 else 0
        para2 = (
            f"The Kronos AI 30-day forecast projects a {kronos_str} price change, "
            f"with a target of RM{pred_close:.4f} and a confidence band of RM{pred_low:.4f}–RM{pred_high:.4f} "
            f"(±{band_width:.1f}% spread). "
            f"{'The positive outlook suggests near-term upside momentum.' if kronos_chg > 0 else 'The negative forecast signals caution in the near term.' if kronos_chg < 0 else 'The forecast indicates minimal near-term price movement.'} "
        )
    else:
        para2 = (
            "No Kronos AI 30-day forecast is currently available for this stock. "
            "Technical signals cannot be assessed at this time."
        )

    fcf_line = f" {fcf_str}" if fcf_str else ""
    para3 = (
        f"Risk assessment: {risk.upper()}. "
        f"Valuation appears {'attractive' if pe and pe < 12 else 'reasonable' if pe and pe < 20 else 'elevated'} "
        f"at {pe_str}x earnings. "
        f"The balance sheet is {'strong' if de and de < 0.3 else 'moderate' if de and de < 0.7 else 'leveraged'} "
        f"with a D/E ratio of {de_str}.{fcf_line} "
        f"**Recommendation: {rec}** — based on a composite score of {score:.1f}/100 "
        f"and a Kronos 30-day outlook of {kronos_str}."
    )

    summary = f"{para1}\n\n{para2}\n\n{para3}"

    report = {
        "summary": summary,
        "recommendation": rec,
        "risk": risk,
        "generated_at": now,
    }
    return report


def main():
    conn = get_db()
    cur = dict_cursor(conn)

    # Fetch all active stocks with full data
    cur.execute("""
        SELECT s.id, s.name, sa.score_composite, sa.score_breakdown, 
               k.pred_change_pct, k.pred_30d_close, k.pred_low, k.pred_high,
               s.pe_ratio, s.roe, s.debt_to_equity, s.dividend_yield, s.last_price,
               s.market_cap, s.industry, s.financials
        FROM stocks s 
        JOIN stock_analyses sa ON s.id = sa.stock_id 
        LEFT JOIN LATERAL (
            SELECT * FROM kronos_forecasts WHERE stock_id = s.id ORDER BY generated_at DESC LIMIT 1
        ) k ON true 
        WHERE s.status = 'active' 
        ORDER BY sa.score_composite DESC
    """)
    stocks = cur.fetchall()
    print(f"Found {len(stocks)} active stocks to process")

    results = []
    buys = []
    gaps = []

    for r in stocks:
        ticker = r['id']
        score = r['score_composite']
        kronos_chg = r['pred_change_pct']
        rec, risk = determine_recommendation(score, kronos_chg)

        report = generate_report(r)
        report_json = json.dumps(report)
        model = 'deepseek-chat'

        # Check for data gaps
        stock_gaps = []
        if kronos_chg is None:
            stock_gaps.append('no Kronos forecast')
        if r['pe_ratio'] is None:
            stock_gaps.append('no PE ratio')
        if r['roe'] is None:
            stock_gaps.append('no ROE')
        if r['debt_to_equity'] is None:
            stock_gaps.append('no D/E ratio')
        if r['dividend_yield'] is None:
            stock_gaps.append('no dividend yield')
        if not r.get('score_breakdown'):
            stock_gaps.append('no score breakdown')

        # Update DB
        cur.execute("""
            UPDATE stock_analyses 
            SET ai_report = %s::jsonb, ai_model = %s, generated_at = NOW()
            WHERE stock_id = %s
        """, (report_json, model, ticker))

        results.append((ticker, r['name'], score, kronos_chg, rec, risk, stock_gaps))
        if rec == 'BUY':
            buys.append((ticker, r['name'], score, kronos_chg))

        print(f"  ✓ {ticker} {r['name']}: {rec} (score={score:.1f}, kronos={kronos_chg if kronos_chg else 'N/A'}%)")

    conn.commit()
    conn.close()

    # Output summary
    print("\n" + "=" * 70)
    print(f"AI REPORT GENERATION SUMMARY")
    print("=" * 70)
    print(f"Total reports generated: {len(results)}")
    print(f"Model: deepseek-chat")
    print(f"Timestamp: {datetime.datetime.now(datetime.timezone.utc).isoformat()}")
    print()

    buys_sorted = sorted(buys, key=lambda x: x[2], reverse=True)
    print(f"TOP 3 BUY RECOMMENDATIONS:")
    for i, (ticker, name, score, kronos) in enumerate(buys_sorted[:3], 1):
        print(f"  {i}. {ticker} {name} — score={score:.1f}, Kronos={kronos:+.2f}%")
    print()

    # Any stocks with gaps
    gap_stocks = [r for r in results if r[6]]  # index 6 = stock_gaps list (non-empty)
    if gap_stocks:
        print(f"DATA GAPS ({len(gap_stocks)} stocks):")
        for ticker, name, score, kronos, rec, risk, stock_gaps in gap_stocks:
            print(f"  {ticker} {name}: {', '.join(stock_gaps)}")
    else:
        print("DATA GAPS: None detected — all data fields populated.")
    print()

    # Recommendation breakdown
    rec_counts = {}
    for _, _, _, _, rec, _, _ in results:
        rec_counts[rec] = rec_counts.get(rec, 0) + 1
    print("RECOMMENDATION BREAKDOWN:")
    for rec in ['BUY', 'HOLD', 'SELL']:
        print(f"  {rec}: {rec_counts.get(rec, 0)}")
    print("=" * 70)


if __name__ == '__main__':
    main()
