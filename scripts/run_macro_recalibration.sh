#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# Macro Score Re-Calibration — weekly cron
# Checks macro_signals.json for >5% moves in key indicators,
# maps to affected industries, triggers industry_scorer.py,
# and reports results.
# ──────────────────────────────────────────────────────────────
set -euo pipefail

ROOT="/Users/munkevin/xiongit/divvy"
MACRO_FILE="$ROOT/data/macro_signals.json"
MATRIX_FILE="$ROOT/data/industry_matrix.json"
VENV_PYTHON="$ROOT/.venv/bin/python3"
REPORT="/tmp/macro_recal_report.txt"

# Key indicators to monitor (the ones mentioned in the task)
KEY_INDICATORS=("brent_crude" "usd_myr" "sox_index" "fb_klci")

echo "=== Macro Score Re-Calibration $(date '+%Y-%m-%d %H:%M') ==="
echo ""

# ── Step 1: Check macro_signals.json exists ──
if [ ! -f "$MACRO_FILE" ]; then
  echo "[ERROR] macro_signals.json not found at $MACRO_FILE"
  echo "Run macro_fetcher.py first."
  exit 1
fi

# ── Step 2: Parse signals and detect >5% moves ──
echo "Checking signals for >5% moves..."

MOVES_FOUND=false
MOVE_DETAILS=""

for key in "${KEY_INDICATORS[@]}"; do
  # Get change_pct from JSON
  change_pct=$($VENV_PYTHON -c "
import json, sys
m = json.load(open('$MACRO_FILE'))
s = m.get('signals', {}).get('$key')
if s:
  cp = s.get('change_pct', 0)
  trend_5d = s.get('trend_5d_pct', 0)
  # Use the larger of daily change and 5d trend
  value = max(abs(cp), abs(trend_5d)) if abs(trend_5d) > abs(cp) else abs(cp)
  print(f\"{value}|{cp}|{trend_5d}|{s.get('value', 'N/A')}|{s.get('unit', '')}\")
else:
  print('0|0|0|0|0')
")

  if [ -z "$change_pct" ]; then
    continue
  fi

  IFS='|' read -r max_chg daily_chg trend_5d current_value unit <<< "$change_pct"
  max_chg=$(echo "$max_chg" | head -1 | xargs)

  # Compare as float
  threshold_met=$($VENV_PYTHON -c "print('yes' if float('$max_chg') > 5.0 else 'no')")

  direction="▲"
  if [ "$(echo "$daily_chg < 0" | $VENV_PYTHON -c "import sys; print('yes' if float(sys.stdin.read().strip()) < 0 else 'no')" 2>/dev/null || echo "no")" = "yes" ]; then
    direction="▼"
  fi

  if [ "$threshold_met" = "yes" ]; then
    MOVES_FOUND=true
    line="${direction} $key: ${current_value} ${unit} (daily: ${daily_chg}%, 5d: ${trend_5d}%)"
    MOVE_DETAILS+="${line}"$'\n'
    echo "  SIGNIFICANT MOVE: $line"
  else
    echo "  OK: $key (${max_chg}% — within threshold)"
  fi
done

echo ""

# ── Step 3: Map to affected industries ──
if [ "$MOVES_FOUND" = true ]; then
  echo "Mapping macro moves to affected industries..."

  AFFECTED_INDUSTRIES=$($VENV_PYTHON -c "
import json

macro = json.load(open('$MACRO_FILE'))
matrix = json.load(open('$MATRIX_FILE'))

signals = macro.get('signals', {})

# Build list of indicators that moved >5%
key_indicators = ['brent_crude', 'usd_myr', 'sox_index', 'fb_klci']
moved = []
for k in key_indicators:
  s = signals.get(k)
  if s:
    cp = abs(s.get('change_pct', 0))
    trend = abs(s.get('trend_5d_pct', 0))
    if max(cp, trend) > 5.0:
      moved.append(k)

# Map to affected industries (any industry with beta > 0 for these signals)
affected = set()
for ind_name, ind in matrix.get('industries', {}).items():
  sens = ind.get('macro_sensitivity', {})
  for mk in moved:
    if mk in sens and sens[mk] > 0:
      affected.add(ind_name)

print('|'.join(sorted(affected)))
")

  echo "  Affected industries: ${AFFECTED_INDUSTRIES//|/, }"
  echo ""

  # ── Step 4: Run industry_scorer.py ──
  echo "Running industry scorer..."
  echo ""
  cd "$ROOT"
  $VENV_PYTHON -u scripts/industry_scorer.py 2>&1

  echo ""
  echo "=== Re-Calibration complete — affected industries rescored ==="
  echo "Trigger signals:"
  echo "$MOVE_DETAILS"
  echo "Affected industries: ${AFFECTED_INDUSTRIES//|/, }"
else
  echo "No significant macro moves detected. Skipping recalibration."
  echo ""
  echo "[SILENT]"
fi
