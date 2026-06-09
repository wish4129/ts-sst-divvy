"""Persona DB helpers — read/write persona configs and holdings from Supabase.

Replaces portfolios.json for all persona data. DB is the single source of truth.
"""
import json
from db import get_db

SHORT_TO_TICKER = {
    'MAYBANK': '1155.KL', 'AXREIT': '5106.KL', 'YTLPOWR': '6742.KL',
    'INSAS': '3379.KL', 'LIIHEN': '7089.KL', 'SCIENTEX': '4731.KL',
    'GENETEC': '0104.KL', 'KLK': '2445.KL', 'INARI': '0166.KL',
    'SIME': '4197.KL', 'MAGNI': '7087.KL', 'MBMR': '5983.KL',
    'AME': '5293.KL', 'DELEUM': '5132.KL', 'WASCO': '5142.KL',
    'KIPREIT': '5280.KL', 'INTA': 'INTA.KL',
    'RHB': '1066.KL', 'PADINI': '7052.KL',
    'GAMUDA': '5398.KL', 'MATRIX': '5236.KL',
    'PBBANK': '1295.KL', 'TIME': '5031.KL', 'SCICOM': '0099.KL',
    'SEM': '5250.KL', 'HEINEKEN': '3255.KL',
}

TICKER_TO_SHORT = {v: k for k, v in SHORT_TO_TICKER.items()}


def short_to_ticker(short_name: str) -> str:
    """Convert short code (MAYBANK) to ticker (1155.KL)."""
    return SHORT_TO_TICKER.get(short_name, short_name + '.KL')


def ticker_to_short(ticker: str) -> str:
    """Convert ticker (1155.KL) to short code (MAYBANK)."""
    return TICKER_TO_SHORT.get(ticker, ticker.replace('.KL', ''))


def get_stock_list():
    """Get list of (short_name, ticker) for all active/revisit stocks."""
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT id, name FROM stocks WHERE status != 'removed' ORDER BY name")
    stocks = [(ticker_to_short(r[0]), r[0]) for r in cur.fetchall()]
    cur.close()
    db.close()
    return stocks


def get_all_stocks_dict():
    """Get {short_name: {code, name, industry, initial_price}} for all stocks."""
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT id, name, industry, initial_price FROM stocks WHERE status != 'removed'")
    result = {}
    for r in cur.fetchall():
        short = ticker_to_short(r[0])
        result[short] = {
            'code': r[0],
            'name': r[1],
            'industry': r[2] or '',
            'initial': float(r[3] or 0),
        }
    cur.close()
    db.close()
    return result


def get_persona_configs():
    """Get all persona configs as {persona_id: {name, god, style, strategy, rules, ...}}."""
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT persona_id, name, god, style, strategy, rules, initial_capital, cash FROM persona_config ORDER BY persona_id")
    result = {}
    for r in cur.fetchall():
        result[r[0]] = {
            'name': r[1],
            'god': r[2] or '',
            'style': r[3] or '',
            'strategy': r[4] or '',
            'rules': r[5] if isinstance(r[5], dict) else (json.loads(r[5]) if r[5] else {}),
            'initial_capital': float(r[6] or 10000),
            'cash': float(r[7] or 10000),
        }
    cur.close()
    db.close()
    return result


def get_persona_holdings(persona_id: str):
    """Get holdings for a persona as {short_name: {shares, cost, target_pct, note}}."""
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT s.id, s.name, ph.shares, ph.cost_basis, ph.target_pct, ph.note
        FROM persona_holdings ph
        JOIN stocks s ON s.id = ph.stock_id
        WHERE ph.persona_id = %s
    """, (persona_id,))
    result = {}
    for r in cur.fetchall():
        short = ticker_to_short(r[0])
        result[short] = {
            'shares': r[2] or 0,
            'cost': float(r[3] or 0),
            'target_pct': float(r[4] or 0),
            'note': r[5] or '',
        }
    cur.close()
    db.close()
    return result


def get_kronos_forecasts():
    """Get latest Kronos 30-day forecasts for all stocks.
    
    Returns {short_name: {pred_change_pct, pred_30d_close, pred_low, pred_high, pred_volatility}}.
    Uses DISTINCT ON to get the latest forecast per stock from DB.
    Portfolio Manager reads from this function instead of kronos_forecast.json.
    """
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT DISTINCT ON (kf.stock_id) kf.stock_id, kf.pred_change_pct, kf.pred_30d_close,
              kf.pred_low, kf.pred_high, kf.pred_volatility
        FROM kronos_forecasts kf
        ORDER BY kf.stock_id, kf.generated_at DESC
    """)
    result = {}
    for r in cur.fetchall():
        sid = r[0]
        short = ticker_to_short(sid)
        result[short] = {
            'pred_change_pct': float(r[1] or 0),
            'pred_30d_close': float(r[2] or 0),
            'pred_low': float(r[3] or 0),
            'pred_high': float(r[4] or 0),
            'pred_volatility': float(r[5] or 0),
        }
    cur.close()
    db.close()
    return result


def save_persona_holdings(persona_id: str, holdings: dict, cash: float = None):
    """Save persona holdings and cash to DB."""
    db = get_db()
    cur = db.cursor()
    
    for short_name, h in holdings.items():
        ticker = short_to_ticker(short_name)
        cur.execute("""
            INSERT INTO persona_holdings (persona_id, stock_id, shares, cost_basis, target_pct, note, updated_at)
            VALUES (%s,%s,%s,%s,%s,%s,NOW())
            ON CONFLICT (persona_id, stock_id) DO UPDATE SET
                shares=EXCLUDED.shares, cost_basis=EXCLUDED.cost_basis,
                target_pct=EXCLUDED.target_pct, note=EXCLUDED.note,
                updated_at=NOW()
        """, (
            persona_id, ticker,
            h.get('shares', 0),
            h.get('cost', 0),
            h.get('target_pct', 0),
            h.get('note', ''),
        ))
    
    if cash is not None:
        cur.execute("UPDATE persona_config SET cash = %s, updated_at = NOW() WHERE persona_id = %s",
                    (cash, persona_id))
    
    db.commit()
    cur.close()
    db.close()
