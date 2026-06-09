"""Unit tests for run_deep_analysis.py — Deep Analysis Generator.

Tests the pure logic: parse_markdown_report, get_stocks_from_db (mocked DB),
generate_ai_report (mocked API), persona constants, and SECTION_MAP.
Uses unittest.mock to avoid real DeepSeek API and real Supabase calls.
"""

import json
import sys
import urllib.request
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, ANY

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from run_deep_analysis import (
    PERSONAS,
    SECTION_MAP,
    get_stocks_from_db,
    parse_markdown_report,
    generate_ai_report,
)


# ═══════════════════════════════════════════════════════════════
# PERSONAS
# ═══════════════════════════════════════════════════════════════


def test_personas_has_three_personas():
    """PERSONAS must have exactly 3 entries: ares, demeter, athena."""
    assert set(PERSONAS.keys()) == {"ares", "demeter", "athena"}


def test_personas_all_have_style_and_philosophy():
    """Each persona has both 'style' and 'philosophy' keys with string values."""
    for pid, config in PERSONAS.items():
        assert "style" in config, f"{pid}: missing 'style'"
        assert "philosophy" in config, f"{pid}: missing 'philosophy'"
        assert isinstance(config["style"], str) and config["style"]
        assert isinstance(config["philosophy"], str) and config["philosophy"]


# ═══════════════════════════════════════════════════════════════
# SECTION_MAP
# ═══════════════════════════════════════════════════════════════


def test_section_map_has_all_keys():
    """SECTION_MAP must cover all keywords used in parse_markdown_report."""
    assert "introduction" in SECTION_MAP
    assert "history" in SECTION_MAP
    assert "trend" in SECTION_MAP
    assert "strength" in SECTION_MAP
    assert "weakness" in SECTION_MAP
    assert "summary" in SECTION_MAP
    assert "target" in SECTION_MAP


def test_section_map_values_are_valid_keys():
    """All SECTION_MAP values map to valid section keys."""
    valid_keys = {
        "introduction_history", "trend_analysis", "strengths",
        "weaknesses", "summary", "target",
    }
    for key, value in SECTION_MAP.items():
        assert value in valid_keys, f"{key} -> {value} is not a valid key"


# ═══════════════════════════════════════════════════════════════
# parse_markdown_report()
# ═══════════════════════════════════════════════════════════════


def test_parse_markdown_full_valid_report():
    """Full valid markdown with all required sections is parsed correctly."""
    content = """## Introduction & History
MAYBANK is Malaysia's largest bank by assets.

## Trend Analysis
Upward trend with strong institutional buying.

## Strengths
- Market leader in Islamic banking
- Strong dividend history

## Weaknesses
- High exposure to SME loans
- Rising OER

## Summary
BUY at current levels with 12-month target.

## Target
RM 12.50
Cut Loss: RM 10.00
"""
    result = parse_markdown_report(content)
    assert result is not None
    assert "introduction_history" in result
    assert "trend_analysis" in result
    assert "strengths" in result
    assert "weaknesses" in result
    assert "summary" in result
    assert "price_target" in result
    assert "cut_loss" in result
    assert "Market leader" in result["strengths"]


def test_parse_markdown_cut_loss_separated_from_price_target():
    """Cut loss section is separated from price target."""
    content = """## Introduction & History
Test stock

## Trend Analysis
Flat

## Strengths
- Good

## Weaknesses
- None

## Summary
Hold

## Target
RM 10.00
Max Loss: RM 8.00
Risk Management: Stop at 7.50
"""
    result = parse_markdown_report(content)
    assert result is not None
    assert "RM 10.00" in result["price_target"]
    assert "Max Loss" in result["cut_loss"] or "RM 8.00" in result["cut_loss"]
    assert result["cut_loss"] != ""


def test_parse_markdown_missing_required_sections():
    """Missing required sections returns None."""
    content = """## Introduction & History
Test

## Strengths
- Good

## Missing everything else
"""
    result = parse_markdown_report(content)
    assert result is None


def test_parse_markdown_no_target_section():
    """Missing target section returns empty price_target and cut_loss."""
    content = """## Introduction & History
Test stock

## Trend Analysis
Flat

## Strengths
- Good

## Weaknesses
- None

## Summary
Hold
"""
    result = parse_markdown_report(content)
    assert result is not None
    assert result["price_target"] == ""
    assert result["cut_loss"] == ""


def test_parse_markdown_empty_content():
    """Empty or whitespace-only content returns None."""
    assert parse_markdown_report("") is None
    assert parse_markdown_report("   ") is None
    assert parse_markdown_report("\n\n\n") is None


def test_parse_markdown_extra_sections():
    """Extra sections are ignored but required ones still parse."""
    content = """## Introduction & History
Test

## Trend Analysis
Flat trend

## Strengths
- Good

## Weaknesses
- Bad

## Summary
Hold

## Target
RM 5.00

## Disclaimer
Not financial advice
"""
    result = parse_markdown_report(content)
    assert result is not None
    assert "disclaimer" not in result  # extra section should not appear
    assert "introduction_history" in result


def test_parse_markdown_various_header_formats():
    """Headers with different formatting still parse correctly."""
    content = """## Introduction & History
Test

## Trend Analysis
Flat

## Strengths
- One

## Weaknesses
- Two

## Summary
Hold

## Target
RM 10
"""
    result = parse_markdown_report(content)
    assert result is not None
    assert "price_target" in result


def test_parse_markdown_cut_loss_variant_phrases():
    """Different cut-loss phrasings are all caught (stop loss, cut-loss, etc.)."""
    content = """## Introduction & History
Test

## Trend Analysis
Flat

## Strengths
- Good

## Weaknesses
- None

## Summary
Hold

## Target
Price target RM 12.50
Cut-loss: RM 10.00
"""
    result = parse_markdown_report(content)
    assert result is not None
    assert "Cut-loss" in result["cut_loss"]


# ═══════════════════════════════════════════════════════════════
# get_stocks_from_db()
# ═══════════════════════════════════════════════════════════════


@patch("run_deep_analysis.get_db")
def test_get_stocks_from_db_returns_dict(mock_get_db):
    """get_stocks_from_db returns a dict keyed by stock code."""
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    mock_get_db.return_value = mock_conn

    mock_cur.fetchall.return_value = [
        ("1155.KL", "MAYBANK", "Banking", 85),
        ("6742.KL", "YTLPOWR", "Utilities", 72),
    ]

    result = get_stocks_from_db(db_conn=mock_conn)
    assert isinstance(result, dict)
    assert "1155.KL" in result
    assert "6742.KL" in result
    assert len(result) == 2


@patch("run_deep_analysis.get_db")
def test_get_stocks_from_db_fields(mock_get_db):
    """Each stock entry has expected fields with correct types."""
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    mock_get_db.return_value = mock_conn

    mock_cur.fetchall.return_value = [("1155.KL", "MAYBANK", "Banking", 85)]

    result = get_stocks_from_db(db_conn=mock_conn)
    entry = result["1155.KL"]
    assert entry["code"] == "1155.KL"
    assert entry["name"] == "MAYBANK"
    assert entry["industry"] == "Banking"
    assert entry["score_composite"] == 85
    assert isinstance(entry["price"], (int, float))
    assert isinstance(entry["beta"], float)


@patch("run_deep_analysis.get_db")
def test_get_stocks_from_db_empty(mock_get_db):
    """Empty DB returns empty dict, not None."""
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    mock_get_db.return_value = mock_conn

    mock_cur.fetchall.return_value = []

    result = get_stocks_from_db(db_conn=mock_conn)
    assert result == {}


@patch("run_deep_analysis.get_db")
def test_get_stocks_from_db_null_score(mock_get_db):
    """NULL score_composite is handled as 0."""
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    mock_get_db.return_value = mock_conn

    mock_cur.fetchall.return_value = [("1155.KL", "MAYBANK", "Banking", None)]

    result = get_stocks_from_db(db_conn=mock_conn)
    assert result["1155.KL"]["score_composite"] == 0


@patch("run_deep_analysis.get_db")
def test_get_stocks_from_db_null_industry(mock_get_db):
    """NULL industry defaults to empty string."""
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    mock_get_db.return_value = mock_conn

    mock_cur.fetchall.return_value = [("1155.KL", "MAYBANK", None, 70)]

    result = get_stocks_from_db(db_conn=mock_conn)
    assert result["1155.KL"]["industry"] == ""


# ═══════════════════════════════════════════════════════════════
# generate_ai_report()
# ═══════════════════════════════════════════════════════════════

SAMPLE_STOCK_DATA = {
    "code": "1155.KL",
    "name": "MAYBANK",
    "industry": "Banking",
    "price": 10.50,
    "dy": 6.2,
    "score_composite": 85,
    "pe": 12.5,
    "roe": 12.0,
    "de": 0.5,
    "rev_growth": 5.0,
    "eps_growth": 0.08,
    "beta": 0.9,
    "fcf": 1_000_000_000,
    "high52": 11.00,
    "low52": 9.00,
    "mcap": 50_000_000_000,
}

VALID_REPORT_CONTENT = """## Introduction & History
MAYBANK is Malaysia's largest bank.

## Trend Analysis
Strong upward momentum.

## Strengths
- Market leader
- Strong dividend yield

## Weaknesses
- SME loan exposure
- NIM compression

## Summary
BUY with target RM 11.50.

## Target
RM 11.50
Cut Loss: RM 9.50
"""


def _mock_api_response(env_get_value, content=VALID_REPORT_CONTENT):
    """Helper: set up a mock response with the specified content."""
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        "choices": [{"message": {"content": content}}]
    }).encode()
    mock_response.__enter__.return_value = mock_response
    return mock_response


@patch("urllib.request.urlopen")
@patch("run_deep_analysis.os.environ.get")
def test_generate_ai_report_success(mock_env_get, mock_urlopen):
    """Happy path: API returns valid markdown, report is parsed correctly."""
    mock_env_get.return_value = "sk-test-key"
    mock_urlopen.return_value = _mock_api_response("sk-test-key")

    result = generate_ai_report(
        SAMPLE_STOCK_DATA, "GDP: 4.5%", "ares", max_retries=0
    )

    assert result is not None
    assert "introduction_history" in result
    assert "trend_analysis" in result
    assert "strengths" in result
    assert "weaknesses" in result
    assert "summary" in result
    assert "price_target" in result
    assert "cut_loss" in result


@patch("run_deep_analysis.os.environ.get")
def test_generate_ai_report_no_api_key(mock_env_get):
    """No API key available returns None."""
    mock_env_get.return_value = ""
    with patch("run_deep_analysis.Path.exists", return_value=False):
        result = generate_ai_report(
            SAMPLE_STOCK_DATA, "GDP: 4.5%", "ares", max_retries=0
        )
    assert result is None


@patch("run_deep_analysis.os.environ.get")
@patch("run_deep_analysis.Path.exists")
@patch("run_deep_analysis.Path.read_text")
@patch("urllib.request.urlopen")
def test_generate_ai_report_api_key_from_env_file(
    mock_urlopen, mock_read, mock_exists, mock_env_get
):
    """Falls back to ~/.hermes/.env when DEEPSEEK_API_KEY env var is empty."""
    mock_env_get.return_value = ""
    mock_exists.return_value = True
    mock_read.return_value = 'DEEPSEEK_API_KEY="sk-test-from-env"\n'
    mock_urlopen.return_value = _mock_api_response("sk-test-from-env")

    result = generate_ai_report(
        SAMPLE_STOCK_DATA, "GDP: 4.5%", "ares", max_retries=0
    )
    assert result is not None


@patch("urllib.request.urlopen")
@patch("run_deep_analysis.os.environ.get")
def test_generate_ai_report_empty_response(mock_env_get, mock_urlopen):
    """Empty API response (no content) returns None after retries."""
    mock_env_get.return_value = "sk-test-key"
    mock_urlopen.return_value = _mock_api_response("sk-test-key", content="")

    result = generate_ai_report(
        SAMPLE_STOCK_DATA, "GDP: 4.5%", "ares", max_retries=1
    )
    assert result is None


@patch("urllib.request.urlopen")
@patch("run_deep_analysis.os.environ.get")
def test_generate_ai_report_malformed_response(mock_env_get, mock_urlopen):
    """Malformed API response (missing key headers) returns None after retries."""
    mock_env_get.return_value = "sk-test-key"

    bad_content = """## Introduction & History
Test

## Only one section
"""
    mock_urlopen.return_value = _mock_api_response("sk-test-key", content=bad_content)

    result = generate_ai_report(
        SAMPLE_STOCK_DATA, "GDP: 4.5%", "ares", max_retries=1
    )
    assert result is None


@patch("urllib.request.urlopen")
@patch("run_deep_analysis.os.environ.get")
def test_generate_ai_report_retries_on_failure(mock_env_get, mock_urlopen):
    """generate_ai_report retries up to max_retries times."""
    mock_env_get.return_value = "sk-test-key"

    # Fail on every attempt — urlopen raises an exception
    mock_urlopen.side_effect = Exception("API timeout")

    result = generate_ai_report(
        SAMPLE_STOCK_DATA, "GDP: 4.5%", "ares", max_retries=2
    )

    # Should have retried 3 times (initial + 2 retries) then returned None
    assert result is None
    assert mock_urlopen.call_count == 3


@patch("urllib.request.urlopen")
@patch("run_deep_analysis.os.environ.get")
def test_generate_ai_report_all_personas(mock_env_get, mock_urlopen):
    """generate_ai_report works for all three personas."""
    mock_env_get.return_value = "sk-test-key"
    mock_urlopen.return_value = _mock_api_response("sk-test-key")

    for persona in ["ares", "demeter", "athena"]:
        result = generate_ai_report(
            SAMPLE_STOCK_DATA, "GDP: 4.5%", persona, max_retries=0
        )
        assert result is not None, f"Failed for persona={persona}"


@patch("urllib.request.urlopen")
@patch("run_deep_analysis.os.environ.get")
def test_generate_ai_report_invalid_persona(mock_env_get, mock_urlopen):
    """Invalid persona triggers KeyError."""
    mock_env_get.return_value = "sk-test-key"

    with pytest.raises(KeyError):
        generate_ai_report(
            SAMPLE_STOCK_DATA, "GDP: 4.5%", "nonexistent", max_retries=0
        )


@patch("urllib.request.urlopen")
@patch("run_deep_analysis.os.environ.get")
def test_generate_ai_report_zero_stock_data(mock_env_get, mock_urlopen):
    """Works with zero-filled stock data (edge case)."""
    mock_env_get.return_value = "sk-test-key"
    mock_urlopen.return_value = _mock_api_response("sk-test-key")

    zero_data = dict(SAMPLE_STOCK_DATA)
    for k in ["price", "dy", "score_composite", "pe", "roe", "de",
              "rev_growth", "eps_growth", "fcf", "high52", "low52", "mcap"]:
        zero_data[k] = 0
    zero_data["beta"] = 0.0
    zero_data["code"] = "0000.KL"
    zero_data["name"] = "ZERO"
    zero_data["industry"] = ""

    result = generate_ai_report(
        zero_data, "No macro data", "demeter", max_retries=0
    )
    assert result is not None
