"""Clean portfolios.json: remove INARI, round all shares to 100-lot."""
import json
from pathlib import Path

LOT = 100
PATH = Path('scripts/portfolios.json')

data = json.loads(PATH.read_text())

# Remove INARI from stocks
data['stocks'].pop('INARI', None)

# Round all persona holdings
for pid, persona in data.get('personas', {}).items():
    to_remove = []
    for name, h in persona.get('holdings', {}).items():
        rounded = (h['shares'] // LOT) * LOT
        if rounded < LOT:
            to_remove.append(name)
            print(f"  {pid} {name}: {h['shares']} → REMOVED (< 1 lot)")
        elif rounded != h['shares']:
            print(f"  {pid} {name}: {h['shares']} → {rounded}")
            h['shares'] = rounded
    for name in to_remove:
        del persona['holdings'][name]

PATH.write_text(json.dumps(data, indent=2))
print(f"\nCleaned {PATH}")
