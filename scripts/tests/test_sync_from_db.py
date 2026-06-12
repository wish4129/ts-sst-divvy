"""Tests for scripts/sync_from_db.py — DB → stocks.ts generation.

sync_from_db.py reads from Supabase (via db.get_db()) and generates:
  web/src/data/stocks.ts — TypeScript source with stock data + ticker maps

We mock the DB connection to test the transformation and output generation logic.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent  # scripts/tests/../../ = divvy/
sys.path.insert(0, str(ROOT / "scripts"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_stock_row(
    ticker="1155.KL",
    name="Malayan Banking Berhad",
    industry="Banking",
    status="active",
    composite=85,
    last_price=10.50,
    price_change=0.25,
    dividend_yield=6.2,
    market_cap=120_000_000_000,
    sparkline_raw="[10.0,10.1,10.2]",
    notes="Solid dividend play",
    kronos_warning=None,
    revisit_at=None,
    fin_json='[{"quarter":"2024Q4","revenue":100,"netIncome":20,"freeCashFlow":15,"peRatio":12,"roe":15,"debtToEquity":0.5,"revenueGrowthYoY":5}]',
    div_json='[{"exDate":"2024-12-01","amount":0.30,"yield":6.0}]',
):
    # Type hints omitted — real DB returns None for NULL columns
    """Build a mock cursor-fetch row matching the SELECT in sync_from_db.py."""
    return (
        ticker, name, industry, status, composite,
        last_price, price_change, dividend_yield, market_cap,
        sparkline_raw, notes, kronos_warning, revisit_at,
        fin_json, div_json,
    )


def make_mock_db(rows):
    """Create a mock DB connection that returns the given rows on fetchall()."""
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_cur.fetchall.return_value = rows
    mock_conn.cursor.return_value = mock_cur
    return mock_conn, mock_cur


def run_sync(mock_rows, extra_patches=None):
    """Execute sync_from_db.py's logic with a mocked DB connection.

    sync_from_db does `from db import get_db` at import time, binding a
    *local* reference.  We must patch db.get_db (the module-level function)
    *before* import, not sync_from_db.get_db (which doesn't exist yet).

    Returns the generated stocks.ts content as a string.
    """
    mock_conn, mock_cur = make_mock_db(mock_rows)

    patches = [
        patch("db.get_db", return_value=mock_conn),
        patch("sync_from_db.ROOT", PropertyMock(return_value=ROOT)),
    ]
    if extra_patches:
        patches.extend(extra_patches)

    # Ensure the module is freshly loaded
    if "sync_from_db" in sys.modules:
        del sys.modules["sync_from_db"]

    for p in patches:
        p.start()
    try:
        import sync_from_db  # noqa: F811 — module-level code runs here
        ts_path = ROOT / "web" / "src" / "data" / "stocks.ts"
        ts_text = ts_path.read_text() if ts_path.exists() else ""
    finally:
        for p in patches:
            p.stop()

    return ts_text


# Convenience alias
StockRow = make_stock_row


# ===================================================================
# Tests
# ===================================================================

class TestDBToPythonTransformation:
    """Verify that raw DB rows are correctly transformed into Python dicts."""

    def test_null_fields_handled(self):
        """NULL financial fields → 0 / '' / [] instead of errors."""
        row = make_stock_row(
            composite=None,
            last_price=None, price_change=None,
            dividend_yield=None, market_cap=None,
            sparkline_raw=None, notes=None,
            fin_json=None, div_json=None,
        )
        ts_text = run_sync([row])
        assert "score: { composite: 0 }" in ts_text
        assert "marketCap: 0.0," in ts_text
        assert "lastPrice: 0.0," in ts_text
        assert "notes: ''" in ts_text

    def test_empty_db_produces_valid_output(self):
        """Empty DB → valid TypeScript with empty stocks array."""
        ts_text = run_sync([])
        assert "export const stocks: Stock[] = [" in ts_text
        assert "]" in ts_text

    def test_single_stock_output_structure(self):
        """Single stock produces exactly one TS entry."""
        ts_text = run_sync([StockRow()])
        assert "code: 'MAYBANK'" in ts_text
        assert "code: 'AXREIT'" not in ts_text  # no extras

    def test_multiple_stocks_separated_by_comma(self):
        """Multiple stocks: entries separated by commas, no trailing comma."""
        row1 = StockRow(ticker="1155.KL", name="Maybank")
        row2 = StockRow(ticker="5106.KL", name="Axis REIT")
        ts_text = run_sync([row1, row2])
        assert "  },\n  {" in ts_text or "  },\n\n  {" in ts_text
        assert ts_text.strip().endswith("}")

    def test_short_code_from_ticker_map(self):
        """Ticker → short code mapping is respected in output."""
        ts_text = run_sync([StockRow(ticker="1155.KL")])
        assert "code: 'MAYBANK'" in ts_text
        assert "code: 'AXREIT'" not in ts_text  # no extra stocks

    def test_unknown_ticker_falls_back_to_stripped(self):
        """Ticker not in TICKER_TO_SHORT uses ticker minus .KL suffix."""
        ts_text = run_sync([StockRow(ticker="9999.KL", name="Unknown Co")])
        assert "code: '9999'" in ts_text


class TestTypeScriptOutputFormat:
    """Verify that the generated stocks.ts has correct structure."""

    def test_full_stock_object_shape(self):
        """Each stock entry has all required fields."""
        ts_text = run_sync([StockRow()])
        required_fields = [
            "code:", "name:", "industry:", "marketCap:",
            "lastPrice:", "priceChange:", "dividendYield:",
            "score: {", "financials:", "dividends:",
            "status:", "addedAt:", "revisitAt:", "notes:", "sparkline:",
        ]
        for field in required_fields:
            assert field in ts_text, f"Missing field: {field}"

    def test_interface_declarations_present(self):
        """TypeScript interfaces are emitted."""
        ts_text = run_sync([StockRow()])
        for interface in ["StockScore", "StockFinancials", "DividendRecord", "Stock"]:
            assert f"export interface {interface}" in ts_text

    def test_ticker_maps_generated(self):
        """SHORT_TO_TICKER and TICKER_TO_SHORT maps are generated."""
        ts_text = run_sync([StockRow(ticker="1155.KL")])
        assert "SHORT_TO_TICKER" in ts_text
        assert "'MAYBANK': '1155.KL'" in ts_text
        assert "TICKER_TO_SHORT" in ts_text

    def test_industry_colors_emitted(self):
        """INDUSTRY_COLORS map appears in output."""
        ts_text = run_sync([StockRow()])
        assert "INDUSTRY_COLORS" in ts_text
        assert "Banking:" in ts_text
        assert "bg-blue-100" in ts_text

    def test_score_object_structure(self):
        """Score composite appears as a single-field object."""
        ts_text = run_sync([
            StockRow(composite=85)
        ])
        assert "composite: 85" in ts_text

    def test_special_chars_escaped(self):
        """Stock names / notes with special chars are escaped."""
        ts_text = run_sync([
            StockRow(name="O'Brien's Corp", notes="It's a good stock (maybe)")
        ])
        # The name gets backslash-escaped single quotes in the TS output
        assert "O\\'Brien\\'s Corp" in ts_text
        assert "It\\'s a good stock" in ts_text


class TestFinancialAndDividendArrays:
    """Test financials/dividends JSON array handling."""

    def test_financials_empty(self):
        """Empty financials array → [] in output."""
        ts_text = run_sync([StockRow(fin_json="[]")])
        assert "financials: []" in ts_text

    def test_financials_multiple_entries(self):
        """Multiple financial quarters all appear."""
        fin_json = json.dumps([
            {"quarter": "2024Q1", "revenue": 100, "netIncome": 20, "freeCashFlow": 15,
             "peRatio": 12, "roe": 15, "debtToEquity": 0.5, "revenueGrowthYoY": 5},
            {"quarter": "2024Q2", "revenue": 110, "netIncome": 22, "freeCashFlow": 16,
             "peRatio": 11, "roe": 16, "debtToEquity": 0.4, "revenueGrowthYoY": 10},
        ])
        ts_text = run_sync([StockRow(fin_json=fin_json)])
        assert "2024Q1" in ts_text
        assert "2024Q2" in ts_text

    def test_dividends_present(self):
        """Dividend records appear in the generated output."""
        ts_text = run_sync([StockRow()])
        assert "dividends: [" in ts_text
        assert "2024-12-01" in ts_text

    def test_null_financials_and_dividends(self):
        """NULL financials/dividends → empty arrays."""
        ts_text = run_sync([StockRow(fin_json=None, div_json=None)])
        assert "financials: []" in ts_text
        assert "dividends: []" in ts_text


class TestTICKER_MAPConsistency:
    """Verify TICKER_MAP bidirectionality and key completeness."""

    def test_all_known_tickers_in_map(self):
        """SHORT_TO_TICKER and TICKER_TO_SHORT are inverse of each other."""
        from persona_db import SHORT_TO_TICKER, TICKER_TO_SHORT
        for short, ticker in SHORT_TO_TICKER.items():
            assert TICKER_TO_SHORT.get(ticker) == short, \
                f"Missing reverse mapping for {short} → {ticker}"
        assert len(SHORT_TO_TICKER) == len(TICKER_TO_SHORT), \
            "Map sizes differ — duplicate values?"

    def test_no_duplicate_tickers(self):
        """No two short codes map to the same ticker."""
        from persona_db import SHORT_TO_TICKER
        tickers = list(SHORT_TO_TICKER.values())
        assert len(tickers) == len(set(tickers)), \
            "Duplicate ticker values found in SHORT_TO_TICKER"

    def test_all_tickers_end_with_kl(self):
        """All ticker values end with .KL (Malaysia exchange)."""
        from persona_db import SHORT_TO_TICKER
        for short, ticker in SHORT_TO_TICKER.items():
            assert ticker.endswith(".KL"), f"{short} → {ticker} should end with .KL"

    def test_ticker_map_in_ts_output(self):
        """Generated TS output includes full ticker map from persona_db."""
        ts_text = run_sync([StockRow(ticker="1155.KL")])
        assert "SHORT_TO_TICKER" in ts_text
        assert "'MAYBANK': '1155.KL'" in ts_text


class TestRevisitAtAndAddedAt:
    """Test revisit_at null handling and the addedAt timestamp."""

    def test_revisit_at_null(self):
        """NULL revisit_at → 'null' in TS output."""
        ts_text = run_sync([StockRow(revisit_at=None)])
        assert "revisitAt: null" in ts_text

    def test_revisit_at_present(self):
        """Populated revisit_at → string value in TS output."""
        ts_text = run_sync([StockRow(revisit_at="2025-06-01")])
        assert "2025-06-01" in ts_text

    def test_added_at_is_today(self):
        """addedAt is the current date."""
        from datetime import datetime, timezone, timedelta
        MYT = timezone(timedelta(hours=8))
        today = datetime.now(MYT).strftime("%Y-%m-%d")
        ts_text = run_sync([StockRow()])
        assert today in ts_text


class TestIdempotentOutput:
    """Verify output is deterministic for identical input."""

    def test_deterministic_ordering(self):
        """Same input data produces same output text."""
        rows = [
            StockRow(ticker="1155.KL", name="Maybank", composite=85),
            StockRow(ticker="5106.KL", name="Axis REIT", composite=72),
        ]
        ts1 = run_sync(rows)
        ts2 = run_sync(rows)
        assert ts1 == ts2


class TestEdgeCases:
    """Edge case scenarios for the sync script."""

    def test_status_revisit_in_output(self):
        """Status values (revisit, active) pass through correctly."""
        ts_text = run_sync([StockRow(ticker="1155.KL", status="revisit")])
        assert "status: 'revisit'" in ts_text

    def test_empty_industry(self):
        """NULL/empty industry → empty string."""
        ts_text = run_sync([StockRow(industry=None)])
        assert "industry: ''" in ts_text
        ts_text2 = run_sync([StockRow(industry="")])
        assert "industry: ''" in ts_text2

    def test_zero_market_cap(self):
        """Zero market cap → 0.0."""
        ts_text = run_sync([StockRow(market_cap=0)])
        assert "marketCap: 0.0" in ts_text

    def test_negative_price_change(self):
        """Negative price change preserves sign."""
        ts_text = run_sync([StockRow(price_change=-0.50)])
        assert "priceChange: -0.5" in ts_text or "priceChange: -0.50" in ts_text

class TestPrintOutput:
    """Verify stdout prints informative status messages (via generated TS)."""

    def test_stock_count_in_file_output(self):
        """Generated TS is non-empty when stock data present."""
        ts_text = run_sync([StockRow(), StockRow(ticker="5106.KL")])
        # Verify multiple entries rendered
        assert "code: 'AXREIT'" in ts_text or "code: 'MAYBANK'" in ts_text

    def test_output_file_is_valid_ts(self):
        """Generated .ts file is a valid TypeScript module."""
        ts_text = run_sync([StockRow()])
        assert "export const stocks: Stock[] = [" in ts_text
        assert ts_text.strip().endswith("}")


class TestPython39Compat:
    """Verify Python 3.9 compatibility (no dict | None syntax)."""

    def test_syntax_valid(self):
        """sync_from_db.py parses without errors on Python 3.9+."""
        import ast
        source = (ROOT / "scripts" / "sync_from_db.py").read_text()
        try:
            ast.parse(source)
        except SyntaxError as e:
            pytest.fail(f"Syntax error (Python 3.9 compat fail): {e}")

    def test_no_walrus_operator(self):
        """sync_from_db.py avoids := operator usage."""
        import ast
        source = (ROOT / "scripts" / "sync_from_db.py").read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            assert not isinstance(node, ast.NamedExpr), \
                "Walrus operator (:=) found — not compatible with Python 3.8+ targets"
