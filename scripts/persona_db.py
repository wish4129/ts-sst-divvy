"""Persona DB helpers — stock ticker maps and DB queries.

Replaces the original persona_db.py that was deleted in commit 347804fe.
The original had persona_config/persona_holdings functions for Ares/Athena/Demeter
portfolios which were dropped. This file retains only the ticker maps and
stock-level queries that other scripts still depend on.
"""
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
    cur.execute("SELECT id, name FROM stocks WHERE status NOT IN ('removed', 'data_missing') ORDER BY name")
    stocks = [(ticker_to_short(r[0]), r[0]) for r in cur.fetchall()]
    cur.close()
    db.close()
    return stocks


def get_all_stocks_dict():
    """Get {short_name: {code, name, industry, initial_price}} for all stocks."""
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT id, name, industry, initial_price FROM stocks WHERE status NOT IN ('removed', 'data_missing')")
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
