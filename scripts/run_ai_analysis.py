"""Run deep analysis with DeepSeek API key from Hermes .env."""
import os, subprocess, sys
from pathlib import Path

# Read key from Hermes .env
env_path = Path.home() / '.hermes' / '.env'
key = None
with open(env_path) as f:
    for line in f:
        if line.startswith('DEEPSEEK_API_KEY'):
            key = line.strip().split('=', 1)[1].strip().strip('"').strip("'")
            break

if not key:
    print('DEEPSEEK_API_KEY not found in ~/.hermes/.env')
    sys.exit(1)

# Run analysis with key
env = os.environ.copy()
env['DEEPSEEK_API_KEY'] = key
result = subprocess.run(
    [str(Path(__file__).resolve().parent.parent / '.venv' / 'bin' / 'python3'), str(Path(__file__).resolve().parent / 'run_deep_analysis.py')],
    cwd=Path(__file__).resolve().parent.parent,
    env=env,
    capture_output=True, text=True, timeout=600
)
print(result.stdout)
if result.stderr:
    print(result.stderr)
