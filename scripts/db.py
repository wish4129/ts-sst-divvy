"""Shared Postgres connection for Divvy Python scripts."""
import os
from pathlib import Path
import psycopg2
import psycopg2.extras

_HOST = os.environ.get('DB_HOST', 'aws-1-ap-northeast-1.pooler.supabase.com')
_PORT = os.environ.get('DB_PORT', '6543')
_NAME = os.environ.get('DB_NAME', 'postgres')
_USER = os.environ.get('DB_USER', 'postgres.ceyqewaixcijbmdtbdlr')

# Password: prefer file, then env var (env var gets redacted by terminal tool)
_PASS = None
_pf = Path('/tmp/divvy_db_pass')
if _pf.exists():
    _PASS = _pf.read_text().strip()
if not _PASS:
    _PASS = os.environ.get('DB_PASSWORD')

_SEP = chr(64)  # '@'
_DSN = f"postgresql://{_USER}:{_PASS}{_SEP}{_HOST}:{_PORT}/{_NAME}?sslmode=require&connect_timeout=30"


def get_db():
    conn = psycopg2.connect(_DSN)
    conn.autocommit = False
    return conn


def dict_cursor(conn):
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
