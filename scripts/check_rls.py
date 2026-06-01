import sys
sys.path.insert(0, 'scripts')
from db import get_db, dict_cursor

db = get_db()
cur = dict_cursor(db)
cur.execute("SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
for r in cur.fetchall():
    print(f"{r['tablename']}: RLS={'ON' if r['rowsecurity'] else 'OFF'}")

cur.execute("SELECT count(*) as cnt FROM pg_policies WHERE schemaname='public'")
print(f"\nTotal policies: {cur.fetchone()['cnt']}")
cur.close()
db.close()
