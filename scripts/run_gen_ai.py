#!/usr/bin/env python3
"""Run gen_ai_reports.py and log progress line by line."""
import subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
result = subprocess.run(
    [str(ROOT / '.venv' / 'bin' / 'python3'), '-u', str(ROOT / 'scripts' / 'gen_ai_reports.py')],
    cwd=str(ROOT), capture_output=False, text=True, timeout=1200
)
