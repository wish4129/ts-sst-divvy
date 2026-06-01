"""Seed the initial user for Divvy."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from db import get_db, dict_cursor
import uuid

db = get_db()
cur = dict_cursor(db)

cur.execute("SELECT id FROM users WHERE name=%s", ('Kevin Mun',))
u = cur.fetchone()
if not u:
    kevin_id = str(uuid.uuid4())
    cur.execute('INSERT INTO users (id, name, email) VALUES (%s, %s, %s)',
                (kevin_id, 'Kevin Mun', 'munkevin@gmail.com'))
    db.commit()
    print(f'Created user: {kevin_id}')
else:
    kevin_id = u['id']
    print(f'Existing user: {kevin_id}')

# Also update portfolio_manager.py references
print(f'User ID: {kevin_id}')
print('Update portfolio_manager.py: WHERE user_id=%s with this ID')

cur.close()
db.close()
