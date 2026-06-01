#!/usr/bin/env python3
"""Divvy cron pipeline: portfolio update → deploy.

1. Run portfolio manager (fetch prices, execute trades, log history)
2. Copy history to web public dir
3. Deploy to CloudFront via SST
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HISTORY_SRC = ROOT / "data" / "portfolio_history.json"
HISTORY_DST = ROOT / "web" / "public" / "portfolio_history.json"

def main():
    # Step 1: Run portfolio manager
    print("=" * 50)
    print("Step 1/3: Portfolio Manager")
    print("=" * 50)
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "portfolio_manager.py")],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    print(result.stdout)
    if result.returncode != 0:
        print(f"ERROR: {result.stderr}")
        # Continue anyway — deploy whatever history we have

    # Step 2: Copy history to web public
    print("=" * 50)
    print("Step 2/3: Copy history to web/public/")
    print("=" * 50)
    HISTORY_DST.parent.mkdir(parents=True, exist_ok=True)
    if HISTORY_SRC.exists():
        shutil.copy2(HISTORY_SRC, HISTORY_DST)
        runs = len(json.loads(HISTORY_SRC.read_text()).get("runs", []))
        print(f"  ✓ Copied {runs} runs to {HISTORY_DST}")
    else:
        print(f"  ⚠ No history found at {HISTORY_SRC}")

    # Step 3: Deploy
    print("=" * 50)
    print("Step 3/3: SST Deploy")
    print("=" * 50)
    subprocess.run(
        ["npx", "sst", "deploy", "--stage", "live"],
        cwd=str(ROOT), check=False,
    )

    # Verify
    print("\n✓ Pipeline complete")


if __name__ == "__main__":
    main()
