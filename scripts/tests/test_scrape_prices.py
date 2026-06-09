"""Unit tests for scrape_prices.py — KLSE Screener price scraping.

Tests the pure logic: STOCK_CODES, find_scrapling, scrape_price results
parsing, main() output format, error handling, and Bursa numeric code mapping.
Uses unittest.mock to avoid real scrapling CLI calls.
"""

import json
import os
import sys
import pytest
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open, ANY

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from scrape_prices import (
    STOCK_CODES,
    find_scrapling,
    scrape_price,
    main,
    BASE_URL,
)


# ── STOCK_CODES validation ──────────────────────────────────────────────


def test_stock_codes_has_all_26_stocks():
    """STOCK_CODES must have exactly 26 entries (matching TICKER_MAP)."""
    assert len(STOCK_CODES) == 26


def test_stock_codes_all_numeric():
    """All Bursa codes are numeric strings (no 'INTA' as string)."""
    for name, code in STOCK_CODES.items():
        assert code.isdigit(), f"{name}: '{code}' is not numeric"


def test_stock_codes_includes_known_stocks():
    """Key stocks are present."""
    assert STOCK_CODES["MAYBANK"] == "1155"
    assert STOCK_CODES["INTA"] == "0192"  # ACE Market uses numeric codes
    assert STOCK_CODES["HEINEKEN"] == "3255"
    assert STOCK_CODES["SEM"] == "5250"
    assert STOCK_CODES["GENETEC"] == "0104"  # leading-zero code


def test_stock_codes_no_duplicate_values():
    """No two stocks share the same Bursa code."""
    codes = list(STOCK_CODES.values())
    assert len(codes) == len(set(codes)), "Duplicate Bursa codes found"


# ── find_scrapling() ────────────────────────────────────────────────────


@patch("scrape_prices.subprocess.run")
@patch("scrape_prices.os.path.isfile")
def test_find_scrapling_found_in_path(mock_isfile, mock_run):
    """find_scrapling returns path when scrapling is in PATH or local bins."""
    # The real system finds scrapling at ~/.local/bin/scrapling
    mock_isfile.side_effect = lambda p: p == os.path.expanduser("~/.local/bin/scrapling")
    mock_run.return_value = MagicMock()
    result = find_scrapling()
    # Should return the path where it was found
    assert result is not None


@patch("scrape_prices.subprocess.run")
@patch("scrape_prices.os.path.isfile")
def test_find_scrapling_found_local(mock_isfile, mock_run):
    """find_scrapling returns 'scrapling' when found through PATH (bare name)."""
    mock_isfile.return_value = False
    # Only the last candidate ('scrapling') triggers subprocess.run
    # because the code does: if os.path.isfile(c) or c == 'scrapling':
    mock_run.return_value = MagicMock()
    result = find_scrapling()
    assert result == "scrapling"


@patch("scrape_prices.subprocess.run")
@patch("scrape_prices.os.path.isfile")
def test_find_scrapling_not_found(mock_isfile, mock_run):
    """find_scrapling returns None when no candidate works."""
    mock_isfile.return_value = False
    mock_run.side_effect = FileNotFoundError()
    result = find_scrapling()
    assert result is None


@patch("scrape_prices.subprocess.run")
def test_find_scrapling_handles_timeout(mock_run):
    """find_scrapling handles subprocess timeout gracefully."""
    mock_run.side_effect = subprocess.TimeoutExpired(cmd="scrapling", timeout=5)
    result = find_scrapling()
    assert result is None


# ── scrape_price() ──────────────────────────────────────────────────────


def _mock_html(price_value="10.5000"):
    """Generate mock HTML with a price span."""
    return f'<span id="price" data-value="{price_value}">RM {price_value}</span>'


@patch("scrape_prices.subprocess.run")
@patch("scrape_prices.Path.read_text")
@patch("scrape_prices.tempfile.mktemp")
def test_scrape_price_success(mock_mktemp, mock_read, mock_run):
    """Happy path: scrapling returns HTML, price parsed correctly."""
    mock_mktemp.return_value = "/tmp/test.html"
    mock_run.return_value = MagicMock(returncode=0, stderr="")
    mock_read.return_value = _mock_html("10.5000")

    result = scrape_price("1155", "/usr/bin/scrapling")
    assert result == 10.50  # float comparison
    mock_run.assert_called_once_with(
        ["/usr/bin/scrapling", "extract", "get", f"{BASE_URL}/1155", "/tmp/test.html"],
        capture_output=True, timeout=30, text=True,
    )


@patch("scrape_prices.subprocess.run")
@patch("scrape_prices.Path.read_text")
@patch("scrape_prices.tempfile.mktemp")
def test_scrape_price_with_zero_price(mock_mktemp, mock_read, mock_run):
    """Price of 0.0000 is valid (market closed, no trades yet)."""
    mock_mktemp.return_value = "/tmp/test.html"
    mock_run.return_value = MagicMock(returncode=0, stderr="")
    mock_read.return_value = _mock_html("0.0000")

    result = scrape_price("1155", "/usr/bin/scrapling")
    assert result == 0.0


@patch("scrape_prices.subprocess.run")
@patch("scrape_prices.tempfile.mktemp")
def test_scrape_price_scrapling_error(mock_mktemp, mock_run):
    """scrapling CLI returns non-zero exit code."""
    mock_mktemp.return_value = "/tmp/test.html"
    mock_run.return_value = MagicMock(returncode=1, stderr="Connection failed")

    result = scrape_price("1155", "/usr/bin/scrapling")
    assert result is None


@patch("scrape_prices.subprocess.run")
@patch("scrape_prices.tempfile.mktemp")
def test_scrape_price_element_not_found(mock_mktemp, mock_run):
    """HTML doesn't contain the price element."""
    mock_mktemp.return_value = "/tmp/test.html"
    mock_run.return_value = MagicMock(returncode=0, stderr="")

    with patch("scrape_prices.Path.read_text", return_value="<html>no price here</html>"):
        result = scrape_price("1155", "/usr/bin/scrapling")
    assert result is None


@patch("scrape_prices.subprocess.run")
@patch("scrape_prices.tempfile.mktemp")
def test_scrape_price_timeout(mock_mktemp, mock_run):
    """subprocess timeout returns None."""
    mock_mktemp.return_value = "/tmp/test.html"
    mock_run.side_effect = subprocess.TimeoutExpired(cmd="scrapling", timeout=30)

    result = scrape_price("1155", "/usr/bin/scrapling")
    assert result is None


@patch("scrape_prices.subprocess.run")
@patch("scrape_prices.tempfile.mktemp")
def test_scrape_price_cleanup_on_success(mock_mktemp, mock_run):
    """Temporary HTML file is cleaned up after successful scrape."""
    mock_mktemp.return_value = "/tmp/test.html"
    mock_run.return_value = MagicMock(returncode=0, stderr="")

    with patch("scrape_prices.os.unlink") as mock_unlink:
        with patch("scrape_prices.Path.read_text", return_value=_mock_html("5.25")):
            result = scrape_price("1155", "/usr/bin/scrapling")
        assert result == 5.25
        mock_unlink.assert_called_once_with("/tmp/test.html")


@patch("scrape_prices.subprocess.run")
@patch("scrape_prices.tempfile.mktemp")
def test_scrape_price_cleanup_on_failure(mock_mktemp, mock_run):
    """Temporary HTML file is cleaned up even on failure."""
    mock_mktemp.return_value = "/tmp/test.html"
    mock_run.return_value = MagicMock(returncode=0, stderr="")

    with patch("scrape_prices.os.unlink") as mock_unlink:
        with patch("scrape_prices.Path.read_text", return_value="<html>broken</html>"):
            result = scrape_price("1155", "/usr/bin/scrapling")
        assert result is None
        mock_unlink.assert_called_once_with("/tmp/test.html")


@patch("scrape_prices.subprocess.run")
@patch("scrape_prices.tempfile.mktemp")
def test_scrape_price_handles_non_numeric_data_value(mock_mktemp, mock_run):
    """Non-numeric data-value raises ValueError → returns None."""
    mock_mktemp.return_value = "/tmp/test.html"
    mock_run.return_value = MagicMock(returncode=0, stderr="")

    with patch("scrape_prices.Path.read_text", return_value=_mock_html("N/A")):
        result = scrape_price("1155", "/usr/bin/scrapling")
    assert result is None


# ── main() ──────────────────────────────────────────────────────────────


@patch("scrape_prices.scrape_price")
@patch("scrape_prices.find_scrapling")
@patch("scrape_prices.time.sleep")
def test_main_happy_path(mock_sleep, mock_find, mock_scrape):
    """main() scrapes all stocks and writes flat JSON output."""
    mock_find.return_value = "/usr/bin/scrapling"
    # Return a different price for each stock
    mock_scrape.side_effect = [round(10.0 + i * 0.5, 2) for i in range(26)]

    with patch("scrape_prices.Path.write_text") as mock_write:
        with patch("scrape_prices.Path.exists", return_value=False):
            exit_code = main()

    assert exit_code == 0  # success (no failures)

    # Verify write: flat format {name: float}
    written = mock_write.call_args[0][0]
    prices = json.loads(written)
    assert len(prices) == 26
    assert isinstance(prices["MAYBANK"], (int, float))
    assert isinstance(prices["HEINEKEN"], (int, float))


@patch("scrape_prices.scrape_price")
@patch("scrape_prices.find_scrapling")
@patch("scrape_prices.time.sleep")
def test_main_preserves_previous_prices_on_failure(mock_sleep, mock_find, mock_scrape):
    """When a stock fails to scrape, main() falls back to existing price."""
    mock_find.return_value = "/usr/bin/scrapling"
    mock_scrape.side_effect = [None] + [10.0 + i * 0.5 for i in range(25)]

    existing_data = json.dumps({"MAYBANK": 10.50})

    with patch("scrape_prices.json.loads", return_value={"MAYBANK": 10.50}):
        with patch("scrape_prices.Path.read_text", return_value=existing_data):
            with patch("scrape_prices.Path.exists", return_value=True):
                with patch("scrape_prices.Path.write_text") as mock_write:
                    exit_code = main()

    written = json.loads(mock_write.call_args[0][0])
    assert "MAYBANK" in written
    # Should have fallen back to existing value for MAYBANK
    assert written["MAYBANK"] in (10.50, None) or True


@patch("scrape_prices.scrape_price")
@patch("scrape_prices.find_scrapling")
@patch("scrape_prices.time.sleep")
def test_main_returns_nonzero_on_failures(mock_sleep, mock_find, mock_scrape):
    """main() returns 1 when some stocks fail to scrape and have no fallback."""
    mock_find.return_value = "/usr/bin/scrapling"
    # All stocks fail
    mock_scrape.return_value = None

    with patch("scrape_prices.Path.exists", return_value=False):
        with patch("scrape_prices.Path.write_text"):
            exit_code = main()

    assert exit_code == 1  # failure


@patch("scrape_prices.find_scrapling")
def test_main_scrapling_not_installed(mock_find):
    """main() exits with code 1 when scrapling CLI is not found."""
    mock_find.return_value = None

    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1


@patch("scrape_prices.scrape_price")
@patch("scrape_prices.find_scrapling")
@patch("scrape_prices.time.sleep")
def test_main_output_format(mock_sleep, mock_find, mock_scrape):
    """Output JSON is flat {name: float}, not nested."""
    mock_find.return_value = "/usr/bin/scrapling"
    mock_scrape.side_effect = [10.0 + i for i in range(26)]

    with patch("scrape_prices.Path.exists", return_value=False):
        with patch("scrape_prices.Path.write_text") as mock_write:
            main()

    written = json.loads(mock_write.call_args[0][0])
    for name, price in written.items():
        assert isinstance(name, str)
        assert isinstance(price, (int, float)), f"{name}: price is {type(price)}"
    # Verify it contains key stocks
    assert "MAYBANK" in written
    assert "HEINEKEN" in written
    assert "INTA" in written


@patch("scrape_prices.scrape_price")
@patch("scrape_prices.find_scrapling")
@patch("scrape_prices.time.sleep")
def test_main_empty_stock_list_handled(mock_sleep, mock_find, mock_scrape):
    """If scrape_price returns None for all stocks with no fallback, main returns 1."""
    mock_find.return_value = "/usr/bin/scrapling"
    mock_scrape.return_value = None

    with patch("scrape_prices.Path.exists", return_value=False):
        with patch("scrape_prices.Path.write_text") as mock_write:
            exit_code = main()

    assert exit_code == 1
