"""Clean up holdings: remove INARI, round all shares to 100-lot minimum."""
import sys
sys.path.insert(0, 'scripts')
from db import get_db, dict_cursor

LOT = 100

db = get_db()
cur = dict_cursor(db)

# 1. Find INARI in stocks
cur.execute("SELECT id, name FROM stocks WHERE name ILIKE '%inari%'")
inari = cur.fetchone()
if inari:
    print(f"Found: {inari['name']} ({inari['id']})")
    
    # Remove INARI from portfolio_holdings
    cur.execute("DELETE FROM portfolio_holdings WHERE stock_id = %s", (inari['id'],))
    print(f"  Removed {cur.rowcount} holding rows")
    
    # Mark INARI stock as removed
    cur.execute("UPDATE stocks SET status = 'removed' WHERE id = %s", (inari['id'],))
    print(f"  Marked stock as removed")
else:
    print("INARI not found in stocks table")

# 2. Find all holdings with odd lots (not divisible by 100)
cur.execute("""
    SELECT ph.portfolio_id, ph.stock_id, ph.shares, ph.avg_cost, ph.target_pct,
           up.persona, s.name as stock_name
    FROM portfolio_holdings ph
    JOIN user_portfolios up ON ph.portfolio_id = up.id
    JOIN stocks s ON ph.stock_id = s.id
    WHERE ph.shares % %s != 0
    ORDER BY up.persona, s.name
""", (LOT,))

odd_lots = cur.fetchall()
print(f"\nOdd-lot holdings: {len(odd_lots)}")

for h in odd_lots:
    rounded = (h['shares'] // LOT) * LOT
    if rounded >= LOT:
        cur.execute(
            "UPDATE portfolio_holdings SET shares = %s WHERE portfolio_id = %s AND stock_id = %s",
            (rounded, h['portfolio_id'], h['stock_id'])
        )
        print(f"  {h['persona']} {h['stock_name']}: {h['shares']} → {rounded}")
    else:
        cur.execute(
            "DELETE FROM portfolio_holdings WHERE portfolio_id = %s AND stock_id = %s",
            (h['portfolio_id'], h['stock_id'])
        )
        print(f"  {h['persona']} {h['stock_name']}: {h['shares']} → REMOVED (< 1 lot)")

# 3. Also round holdings that are already lot-aligned but may have been
# reduced by partial sales to sub-lot levels
cur.execute("""
    SELECT ph.portfolio_id, ph.stock_id, ph.shares, up.persona, s.name as stock_name
    FROM portfolio_holdings ph
    JOIN user_portfolios up ON ph.portfolio_id = up.id
    JOIN stocks s ON ph.stock_id = s.id
    WHERE ph.shares < %s
    ORDER BY up.persona, s.name
""", (LOT,))

sub_lot = cur.fetchall()
for h in sub_lot:
    cur.execute(
        "DELETE FROM portfolio_holdings WHERE portfolio_id = %s AND stock_id = %s",
        (h['portfolio_id'], h['stock_id'])
    )
    print(f"  SUB-LOT {h['persona']} {h['stock_name']}: {h['shares']} → REMOVED")

# 4. Show final state
cur.execute("""
    SELECT up.persona, s.name as stock_name, ph.shares, ph.avg_cost
    FROM portfolio_holdings ph
    JOIN user_portfolios up ON ph.portfolio_id = up.id
    JOIN stocks s ON ph.stock_id = s.id
    ORDER BY up.persona, s.name
""")

print("\n=== Final Holdings ===")
for h in cur.fetchall():
    print(f"  {h['persona']:8s} {h['stock_name']:10s} {h['shares']:6d} @ RM {float(h['avg_cost']):.3f}")

db.commit()
cur.close()
db.close()
print("\nDone. Run portfolio_manager.py to re-export portfolio_history.json")
