#!/bin/bash
cd /Users/munkevin/xiongit/divvy
KEY=$(grep DEEPSEEK_API_KEY /Users/munkevin/.hermes/.env | cut -d= -f2 | tr -d '"'"'"')
export DEEPSEEK_API_KEY="$KEY"
exec .venv/bin/python3 scripts/run_deep_analysis.py 2>&1
