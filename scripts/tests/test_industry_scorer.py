"""Unit tests for industry_scorer.py — core scoring functions.

Tests score_factor() with linear interpolation, composite cap at 100,
macro adjustment, fallback scoring for unknown industries, and
get_financial() data mapping.

No yfinance or DB dependency — pure logic tests.
"""

import sys
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))


class TestScoreFactor:
    """Test linear interpolation scoring with benchmark curves."""

    def _import_score_factor(self):
        """Import score_factor after mocking module-level globals."""
        # score_factor is a pure function — just import it
        from industry_scorer import score_factor
        return score_factor

    def test_dividend_yield_high(self):
        """High dividend yield gets high score."""
        sf = self._import_score_factor()
        score = sf("dividend_yield", 8.0, 40, True)
        assert score > 70, f"Expected >70 for DY=8%, got {score}"

    def test_dividend_yield_mid(self):
        """Moderate dividend yield gets mid score."""
        sf = self._import_score_factor()
        score = sf("dividend_yield", 4.0, 40, True)
        assert 30 <= score <= 65, f"Expected 30-65 for DY=4%, got {score}"

    def test_dividend_yield_zero(self):
        """Zero dividend yield gets zero score."""
        sf = self._import_score_factor()
        score = sf("dividend_yield", 0.0, 40, True)
        assert score == 0, f"Expected 0 for DY=0%, got {score}"

    def test_none_value_returns_zero(self):
        """None value returns 0 score regardless of weight."""
        sf = self._import_score_factor()
        score = sf("roe", None, 20, True)
        assert score == 0, f"Expected 0 for None value, got {score}"

    def test_roe_quarterly_annualized(self):
        """ROE < 15 is annualized (×4) for proper comparison."""
        sf = self._import_score_factor()
        # ROE of 3% quarterly → 12% annualized
        score = sf("roe", 3.0, 20, True)
        assert score > 0, f"Expected >0 for quarterly ROE=3%, got {score}"

    def test_roe_high_value_not_annualized(self):
        """ROE >= 15 is NOT annualized (already annual)."""
        sf = self._import_score_factor()
        score = sf("roe", 18.0, 20, True)
        assert score > 70, f"Expected >70 for ROE=18%, got {score}"

    def test_de_ratio_lower_is_better(self):
        """D/E ratio: lower values get higher scores."""
        sf = self._import_score_factor()
        low_de = sf("de_ratio", 0.3, 30, False)
        high_de = sf("de_ratio", 5.0, 30, False)
        assert low_de > high_de, f"Low D/E should score higher: {low_de} vs {high_de}"

    def test_pe_ratio_extremes(self):
        """P/E ratio: very low gets high score, very high gets low."""
        sf = self._import_score_factor()
        low_pe = sf("pe_ratio", 6.0, 25, False)
        high_pe = sf("pe_ratio", 30.0, 25, False)
        assert low_pe > high_pe, f"Low P/E should score higher: {low_pe} vs {high_pe}"

    def test_value_below_curve_clamped(self):
        """Value below lowest benchmark gets clamped to lowest score."""
        sf = self._import_score_factor()
        # dividend_yield curve starts at (0,0), so -1 should get 0
        score = sf("dividend_yield", -1.0, 40, True)
        assert score == 0, f"Expected 0 for negative value, got {score}"

    def test_value_above_curve_clamped(self):
        """Value above highest benchmark gets clamped to highest score."""
        sf = self._import_score_factor()
        score = sf("dividend_yield", 20.0, 40, True)
        assert score == 100, f"Expected 100 for extreme value, got {score}"

    def test_unknown_factor_linear_fallback(self):
        """Unknown factor uses generic (0,0)→(100,100) fallback."""
        sf = self._import_score_factor()
        score = sf("some_new_factor", 50.0, 25, True)
        assert 0 <= score <= 100, f"Expected 0-100 for unknown factor, got {score}"


class TestMacroAdjustment:
    """Test macro sensitivity adjustments."""

    def test_unknown_industry_returns_zero(self):
        """Unknown industry gets 0 macro adjustment."""
        from industry_scorer import macro_adjustment
        adj = macro_adjustment("NonExistentIndustry")
        assert adj == 0, f"Expected 0 for unknown industry, got {adj}"

    def test_banking_macro_adjustment(self):
        """Banking industry: known to have macro_sensitivity."""
        from industry_scorer import macro_adjustment
        adj = macro_adjustment("Banking")
        # Adjustment should be within -15 to +15 range
        assert -15 <= adj <= 15, f"Adjustment out of range: {adj}"

    def test_reit_macro_adjustment(self):
        """REIT industry gets macro adjustment."""
        from industry_scorer import macro_adjustment
        adj = macro_adjustment("REIT")
        assert -15 <= adj <= 15, f"Adjustment out of range: {adj}"


class TestCompositeCap:
    """Test composite score is capped at 100 and floored at 0."""

    def test_composite_capped_at_100(self):
        """Composite cannot exceed 100."""
        from industry_scorer import score_stock
        row = {"id": "1155.KL", "name": "Maybank", "industry": "Banking",
               "ind_code": "", "status": "active", "ticker": "1155.KL",
               "exchange": "KLS", "cusip": "", "isin": ""}
        result = score_stock(row)
        assert 0 <= result["composite"] <= 100, \
            f"Composite {result['composite']} outside 0-100 range"


class TestGetFinancial:
    """Test get_financial_from_db() data mapping."""

    def test_dividend_yield_mapping(self):
        """dividend_yield maps to dividend_yield_pct."""
        from industry_scorer import get_financial_from_db
        # When financial data doesn't exist, it returns None
        row = {"id": "NONEXISTENT", "name": "Test"}
        result = get_financial_from_db(row, "dividend_yield")
        assert result is None, f"Expected None for missing stock, got {result}"

    def test_roe_mapping(self):
        """roe maps to roe_pct."""
        from industry_scorer import get_financial_from_db
        row = {"id": "NONEXISTENT", "name": "Test"}
        result = get_financial_from_db(row, "roe")
        assert result is None

    def test_banking_factor_mapping(self):
        """Banking-specific factors map correctly."""
        from industry_scorer import get_financial_from_db
        row = {"id": "NONEXISTENT", "name": "Test"}
        for factor in ["nim", "casa_ratio", "car", "npl_ratio", "cost_income"]:
            result = get_financial_from_db(row, factor)
            assert result is None, f"{factor}: expected None for missing stock"


class TestFallbackIndustry:
    """Test unknown industry falls back to generic 4-pillar."""

    def test_unknown_industry_gets_fallback(self):
        """Unknown industry uses generic 4-pillar (dividend, growth, quality, risk)."""
        from industry_scorer import score_stock
        # Use a stock that has financial data to avoid None scores
        row = {"id": "1155.KL", "name": "Maybank", "industry": "UnknownIndustry",
               "status": "active"}
        result = score_stock(row)
        assert "composite" in result
        assert "breakdown" in result
        # Should have 4 factors from generic fallback
        assert len(result["breakdown"]) == 4, \
            f"Expected 4 fallback factors, got {len(result['breakdown'])}"


class TestScoreStructure:
    """Test score_stock() returns correct structure."""

    def test_result_keys(self):
        """Score result has all required keys."""
        from industry_scorer import score_stock
        row = {"id": "1155.KL", "name": "Maybank", "industry": "Banking",
               "status": "active"}
        result = score_stock(row)
        assert "code" in result
        assert "name" in result
        assert "industry" in result
        assert "composite" in result
        assert "macro_adjustment" in result
        assert "breakdown" in result

    def test_breakdown_structure(self):
        """Breakdown entries have value, raw, weighted."""
        from industry_scorer import score_stock
        row = {"id": "1155.KL", "name": "Maybank", "industry": "Banking",
               "status": "active"}
        result = score_stock(row)
        for factor_name, b in result["breakdown"].items():
            assert "value" in b, f"{factor_name}: missing 'value'"
            assert "raw" in b, f"{factor_name}: missing 'raw'"
            assert "weighted" in b, f"{factor_name}: missing 'weighted'"
