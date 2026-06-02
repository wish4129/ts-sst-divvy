#!/usr/bin/env python3
"""Seed bursa_universe with 822 KLSE stocks from SMFA repo (batched)."""
import sys, csv, urllib.request
from psycopg2.extras import execute_values

sys.path.insert(0, 'scripts')
from db import get_db

url = "https://raw.githubusercontent.com/kj-lai/SMFA/master/stock_code_table.csv"
print("Downloading...")
resp = urllib.request.urlopen(url, timeout=30)
content = resp.read().decode('utf-8')

db = get_db()
cur = db.cursor()
reader = csv.DictReader(content.splitlines())

rows = []
for row in reader:
    code = row['code'].strip()
    name = row['name'].strip().replace('+', ' ')
    ticker = f'{code}.KL'
    rows.append((ticker, name))

# Batch insert
execute_values(cur, '''
    INSERT INTO bursa_universe (stock_code, name)
    VALUES %s
    ON CONFLICT (stock_code) DO UPDATE SET name = EXCLUDED.name
''', rows)
print(f'Seeded {len(rows)} stocks')

# Mark existing as analyzed
cur.execute('''
    UPDATE bursa_universe SET has_analysis = TRUE 
    WHERE stock_code IN (SELECT id FROM stocks WHERE status != 'removed')
''')
print(f'Marked {cur.rowcount} as analyzed')

db.commit()
cur.close()
db.close()
print('Done')
