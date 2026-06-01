"""Apply RLS policies one at a time with independent connections."""
import sys
sys.path.insert(0, 'scripts')
from db import get_db

POLICIES = [
    # Public read
    ("stocks", "stocks_read_all", "SELECT", "USING (true)"),
    ("stock_prices", "stock_prices_read_all", "SELECT", "USING (true)"),
    ("kronos_forecasts", "kronos_forecasts_read_all", "SELECT", "USING (true)"),
    ("screener_candidates", "screener_candidates_read_all", "SELECT", "USING (true)"),
    # User portfolios
    ("user_portfolios", "portfolios_select_own", "SELECT", "USING (user_id = auth.uid())"),
    ("user_portfolios", "portfolios_insert_own", "INSERT", "WITH CHECK (user_id = auth.uid())"),
    ("user_portfolios", "portfolios_update_own", "UPDATE", "USING (user_id = auth.uid())"),
    ("user_portfolios", "portfolios_delete_own", "DELETE", "USING (user_id = auth.uid())"),
    # Holdings (via portfolio ownership)
    ("portfolio_holdings", "holdings_select_own", "SELECT",
     "USING (portfolio_id IN (SELECT id FROM user_portfolios WHERE user_id = auth.uid()))"),
    ("portfolio_holdings", "holdings_insert_own", "INSERT",
     "WITH CHECK (portfolio_id IN (SELECT id FROM user_portfolios WHERE user_id = auth.uid()))"),
    ("portfolio_holdings", "holdings_update_own", "UPDATE",
     "USING (portfolio_id IN (SELECT id FROM user_portfolios WHERE user_id = auth.uid()))"),
    ("portfolio_holdings", "holdings_delete_own", "DELETE",
     "USING (portfolio_id IN (SELECT id FROM user_portfolios WHERE user_id = auth.uid()))"),
    # Trades
    ("trades", "trades_select_own", "SELECT",
     "USING (portfolio_id IN (SELECT id FROM user_portfolios WHERE user_id = auth.uid()))"),
    ("trades", "trades_insert_own", "INSERT",
     "WITH CHECK (portfolio_id IN (SELECT id FROM user_portfolios WHERE user_id = auth.uid()))"),
    # Snapshots
    ("portfolio_snapshots", "snapshots_select_own", "SELECT",
     "USING (portfolio_id IN (SELECT id FROM user_portfolios WHERE user_id = auth.uid()))"),
    ("portfolio_snapshots", "snapshots_insert_own", "INSERT",
     "WITH CHECK (portfolio_id IN (SELECT id FROM user_portfolios WHERE user_id = auth.uid()))"),
    # User picks
    ("user_stock_picks", "picks_select_own", "SELECT", "USING (user_id = auth.uid())"),
    ("user_stock_picks", "picks_insert_own", "INSERT", "WITH CHECK (user_id = auth.uid())"),
    ("user_stock_picks", "picks_update_own", "UPDATE", "USING (user_id = auth.uid())"),
    ("user_stock_picks", "picks_delete_own", "DELETE", "USING (user_id = auth.uid())"),
    # Users
    ("users", "users_read_own", "SELECT", "USING (id = auth.uid())"),
    ("users", "users_update_own", "UPDATE", "USING (id = auth.uid())"),
]

for table, name, op, clause in POLICIES:
    db = get_db()
    cur = db.cursor()
    try:
        sql = f'CREATE POLICY "{name}" ON {table} FOR {op} TO authenticated {clause}'
        cur.execute(sql)
        db.commit()
        print(f'+ {name}')
    except Exception as e:
        db.rollback()
        msg = str(e)
        if 'already exists' in msg or 'duplicate' in msg:
            print(f'  {name} (exists)')
        else:
            print(f'ERR {name}: {e}')
    finally:
        cur.close()
        db.close()

print('\nDone')
