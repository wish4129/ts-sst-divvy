"""Clean portfolio_history.json: remove INARI, round all shares to 100-lot."""
import json
from pathlib import Path

LOT = 100
PATH = Path('data/portfolio_history.json')

data = json.loads(PATH.read_text())

for run in data['runs']:
    for pid, snap in run.get('personas', {}).items():
        holdings = snap.get('holdings', {})
        # Remove INARI
        holdings.pop('INARI', None)
        # Round all shares to lot size
        to_remove = []
        for name, h in holdings.items():
            rounded = (h['shares'] // LOT) * LOT
            if rounded < LOT:
                to_remove.append(name)
            else:
                h['shares'] = rounded
                h['invested'] = round(rounded * h['cost'], 2)
                h['current'] = round(rounded * h.get('price', h['cost']), 2)
                h['pnl'] = round(h['current'] - h['invested'], 2)
                if h['invested'] > 0:
                    h['pnl_pct'] = round(((h.get('price', h['cost']) - h['cost']) / h['cost']) * 100, 2)
        for name in to_remove:
            del holdings[name]
        
        # Recalculate totals
        if holdings:
            invested = sum(h['invested'] for h in holdings.values())
            current = sum(h['current'] for h in holdings.values())
            snap['invested'] = round(invested, 2)
            snap['total'] = round(current + snap.get('cash', 0), 2)
            snap['pnl'] = round(snap['total'] - 10000, 2)
            snap['pnl_pct'] = round((snap['pnl'] / 10000) * 100, 2)

PATH.write_text(json.dumps(data, indent=2))
print(f"Cleaned {PATH} — {len(data['runs'])} runs")
