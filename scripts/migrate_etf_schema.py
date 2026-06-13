"""Phase 2: Bursa ETF Schema Migration
Run: python3 scripts/migrate_etf_schema.py

Adds ETF-specific columns to bursa_universe table.
Safe to run on production — only ADD COLUMN operations.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from db import get_db


MIGRATIONS = [
    # Step 1: Add type discriminator
    """ALTER TABLE bursa_universe 
       ADD COLUMN IF NOT EXISTS asset_type TEXT NOT NULL DEFAULT 'stock'""",
    
    # Step 2: ETF-specific columns (nullable, only populated for ETFs)
    """ALTER TABLE bursa_universe 
       ADD COLUMN IF NOT EXISTS etf_category TEXT""",
    """ALTER TABLE bursa_universe 
       ADD COLUMN IF NOT EXISTS expense_ratio NUMERIC""",
    """ALTER TABLE bursa_universe 
       ADD COLUMN IF NOT EXISTS aum NUMERIC""",
    """ALTER TABLE bursa_universe 
       ADD COLUMN IF NOT EXISTS shariah BOOLEAN DEFAULT NULL""",
    """ALTER TABLE bursa_universe 
       ADD COLUMN IF NOT EXISTS return_1y NUMERIC""",
    """ALTER TABLE bursa_universe 
       ADD COLUMN IF NOT EXISTS isin TEXT""",
]


def main():
    db = get_db()
    cur = db.cursor()
    
    print("=== Bursa ETF Schema Migration ===")
    print(f"Applying {len(MIGRATIONS)} migrations...\n")
    
    applied = 0
    errors = 0
    
    for sql in MIGRATIONS:
        try:
            # Check if column already exists (Postgres doesn't have IF NOT EXISTS for ADD COLUMN in older versions)
            table = "bursa_universe"
            col = sql.split("ADD COLUMN IF NOT EXISTS ")[1].split(" ")[0] if "ADD COLUMN IF NOT EXISTS" in sql else ""
            
            if col:
                cur.execute("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = %s AND column_name = %s
                """, (table, col))
                if cur.fetchone():
                    print(f"  ✓ Column '{col}' already exists — skipped")
                    continue
            
            cur.execute(sql)
            print(f"  ✓ {sql[:80]}...")
            applied += 1
        except Exception as e:
            print(f"  ✗ {str(e)[:100]}")
            errors += 1
    
    if applied > 0:
        db.commit()
    
    cur.close()
    db.close()
    
    print(f"\nApplied: {applied}, Errors: {errors}")
    
    # Verify schema
    db2 = get_db()
    c2 = db2.cursor()
    c2.execute("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'bursa_universe'
        ORDER BY ordinal_position
    """)
    print("\nUpdated schema:")
    for row in c2.fetchall():
        print(f"  {row[0]:25s} {row[1]:15s} nullable={row[2]}")
    c2.close()
    db2.close()


if __name__ == "__main__":
    main()
