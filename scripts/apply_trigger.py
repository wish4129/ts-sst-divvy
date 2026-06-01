"""Apply Supabase trigger for auto-creating user profiles."""
import sys
sys.path.insert(0, 'scripts')
from db import get_db

sql = open('scripts/trigger_new_user.sql').read()
db = get_db()
cur = db.cursor()
try:
    cur.execute(sql)
    db.commit()
    print('+ handle_new_user trigger created')
except Exception as e:
    db.rollback()
    print(f'ERR: {e}')
finally:
    cur.close()
    db.close()
