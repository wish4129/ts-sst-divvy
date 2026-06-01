import sys
sys.path.insert(0, 'scripts')
from db import get_db, dict_cursor

db = get_db()
cur = dict_cursor(db)

cur.execute('SELECT count(*) as c FROM stocks')
print(f"stocks: {cur.fetchone()['c']}")

cur.execute('SELECT count(*) as c FROM portfolio_holdings')
print(f"holdings: {cur.fetchone()['c']}")

cur.execute('SELECT count(*) as c FROM user_portfolios')
print(f"portfolios: {cur.fetchone()['c']}")

cur.execute('SELECT count(*) as c FROM trades')
print(f"trades: {cur.fetchone()['c']}")

cur.close()
db.close()
