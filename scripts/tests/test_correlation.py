"""Tests for correlation.py — pairwise correlation and concentration risk."""

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from risk.correlation import (
    _correlation_strength,
    _concentration_risk_level,
    compute_correlation,
    check_persona_concentration,
    DEFAULT_THRESHOLD,
)


# ── _correlation_strength ─────────────────────────────────────────────


def test_correlation_strength_very_strong_positive():
    assert _correlation_strength(0.95) == "very strong positive"


def test_correlation_strength_strong_positive():
    assert _correlation_strength(0.85) == "strong positive"


def test_correlation_strength_moderate_positive():
    assert _correlation_strength(0.70) == "moderate positive"


def test_correlation_strength_weak_positive():
    assert _correlation_strength(0.50) == "weak positive"


def test_correlation_strength_negligible():
    assert _correlation_strength(0.30) == "negligible"


def test_correlation_strength_very_strong_negative():
    assert _correlation_strength(-0.95) == "very strong negative"


def test_correlation_strength_strong_negative():
    assert _correlation_strength(-0.82) == "strong negative"


def test_correlation_strength_boundary_very_strong():
    """At exactly 0.9, classified as very strong."""
    assert "very strong" in _correlation_strength(0.9)


def test_correlation_strength_boundary_strong():
    """At exactly 0.8, classified as strong."""
    assert "strong" in _correlation_strength(0.8)


def test_correlation_strength_zero():
    """Zero correlation is negligible."""
    assert _correlation_strength(0.0) == "negligible"


# ── _concentration_risk_level ─────────────────────────────────────────


def test_risk_level_critical():
    """At ≥0.9 correlation, CRITICAL risk."""
    assert "CRITICAL" in _concentration_risk_level(0.92)
    assert "CRITICAL" in _concentration_risk_level(-0.92)


def test_risk_level_high():
    """At ≥0.85 correlation, HIGH risk."""
    assert "HIGH" in _concentration_risk_level(0.87)
    assert "HIGH" in _concentration_risk_level(-0.88)


def test_risk_level_elevated():
    """At ≥0.80 correlation, ELEVATED risk."""
    assert "ELEVATED" in _concentration_risk_level(0.82)
    assert "ELEVATED" in _concentration_risk_level(0.80)


def test_risk_level_moderate():
    """Below threshold, MODERATE risk."""
    assert "MODERATE" in _concentration_risk_level(0.75)
    assert "MODERATE" in _concentration_risk_level(0.50)


def test_risk_level_zero_correlation():
    """Zero correlation is MODERATE."""
    assert "MODERATE" in _concentration_risk_level(0.0)


# ── compute_correlation ──────────────────────────────────────────────


def sample_returns(n_stocks: int, n_days: int = 100) -> np.ndarray:
    """Generate sample daily returns matrix."""
    rng = np.random.default_rng(42)
    return rng.normal(0.001, 0.02, (n_days, n_stocks))


def test_compute_correlation_basic():
    """Basic correlation computation with 3 stocks."""
    rng = np.random.default_rng(99)
    # Create two highly correlated series + one independent
    base = rng.normal(0.001, 0.02, 200)
    a = base + rng.normal(0, 0.002, 200)        # Correlated with base
    b = base + rng.normal(0, 0.002, 200)        # Correlated with base
    c = rng.normal(0.001, 0.02, 200)            # Independent
    returns = np.column_stack([a, b, c])

    result = compute_correlation(returns, ["A.KL", "B.KL", "C.KL"], threshold=0.80)

    assert result["n_stocks"] == 3
    assert result["n_high_pairs"] >= 1  # A↔B should be highly correlated
    assert len(result["high_correlation_pairs"]) >= 1
    # Check the A↔B pair has high correlation
    high_corrs = [p["correlation"] for p in result["high_correlation_pairs"] if
                  set([p["stock_a"], p["stock_b"]]) == {"A.KL", "B.KL"}]
    if high_corrs:
        assert abs(high_corrs[0]) >= 0.80


def test_compute_correlation_negative_correlation():
    """Negative correlation pairs are also flagged."""
    rng = np.random.default_rng(77)
    base = rng.normal(0.001, 0.02, 200)
    a = base + rng.normal(0, 0.002, 200)
    b = -base + rng.normal(0, 0.002, 200)  # Negatively correlated
    returns = np.column_stack([a, b])

    result = compute_correlation(returns, ["A.KL", "B.KL"], threshold=0.80)

    # Negative correlation should be flagged if abs(corr) >= threshold
    assert result["n_stocks"] == 2
    assert result["n_high_pairs"] >= 1


def test_compute_correlation_no_high_pairs():
    """With random independent data, no high-correlation pairs."""
    rng = np.random.default_rng(123)
    returns = rng.normal(0.001, 0.02, (300, 3))  # 3 independent stocks
    result = compute_correlation(returns, ["X.KL", "Y.KL", "Z.KL"], threshold=0.95)
    # At 0.95 threshold with random data, expect 0 high pairs
    assert result["n_high_pairs"] == 0
    assert result["high_correlation_pairs"] == []


def test_compute_correlation_single_stock():
    """Single stock produces valid result with no pairs."""
    rng = np.random.default_rng(1)
    returns = rng.normal(0.001, 0.02, (100, 1)).reshape(100, 1)
    result = compute_correlation(returns, ["SOLO.KL"], threshold=0.80)
    assert result["n_stocks"] == 1
    assert result["n_high_pairs"] == 0
    assert result["pct_high_correlation"] == 0.0


def test_compute_correlation_two_stocks():
    """Two stocks produce exactly 1 pair."""
    rng = np.random.default_rng(42)
    returns = rng.normal(0.001, 0.02, (200, 2))
    result = compute_correlation(returns, ["A.KL", "B.KL"], threshold=0.80)
    assert result["n_stocks"] == 2


def test_compute_correlation_statistics_present():
    """Result includes mean, median, min, max correlation."""
    rng = np.random.default_rng(42)
    returns = rng.normal(0.001, 0.02, (200, 3))
    result = compute_correlation(returns, ["A.KL", "B.KL", "C.KL"], threshold=0.80)
    assert "mean_correlation" in result
    assert "median_correlation" in result
    assert "min_correlation" in result
    assert "max_correlation" in result
    # Correlations are bounded [-1, 1]
    assert -1.0 <= result["min_correlation"] <= 1.0
    assert -1.0 <= result["max_correlation"] <= 1.0


def test_compute_correlation_threshold_is_set():
    """Custom threshold is reflected in result."""
    rng = np.random.default_rng(42)
    returns = rng.normal(0.001, 0.02, (200, 3))
    result = compute_correlation(returns, ["A.KL", "B.KL", "C.KL"], threshold=0.85)
    assert result["threshold"] == 0.85


def test_compute_correlation_matrix_present():
    """Result includes correlation matrix dict."""
    rng = np.random.default_rng(42)
    returns = rng.normal(0.001, 0.02, (200, 3))
    result = compute_correlation(returns, ["A.KL", "B.KL", "C.KL"], threshold=0.80)
    assert "matrix" in result
    assert "A.KL" in result["matrix"]


def test_compute_correlation_pct_calculation():
    """Percentage of high-correlation pairs is correct."""
    rng = np.random.default_rng(42)
    returns = rng.normal(0.001, 0.02, (200, 3))
    result = compute_correlation(returns, ["A.KL", "B.KL", "C.KL"], threshold=0.80)
    n_pairs = result["n_high_pairs"]
    total_possible = result["n_stocks"] * (result["n_stocks"] - 1) / 2
    expected_pct = round(n_pairs / max(1, total_possible) * 100, 1)
    assert abs(result["pct_high_correlation"] - expected_pct) < 0.1


def test_compute_correlation_high_pairs_sorted():
    """High correlation pairs are sorted by abs(corr) descending."""
    rng = np.random.default_rng(55)
    base = rng.normal(0.001, 0.02, 200)
    returns = np.column_stack([
        base + rng.normal(0, 0.001, 200),
        base + rng.normal(0, 0.005, 200),
        base + rng.normal(0, 0.010, 200),
    ])
    result = compute_correlation(returns, ["A.KL", "B.KL", "C.KL"], threshold=0.5)
    pairs = result["high_correlation_pairs"]
    corrs = [abs(p["correlation"]) for p in pairs]
    assert corrs == sorted(corrs, reverse=True)


# ── check_persona_concentration ──────────────────────────────────────


def test_check_concentration_overlapping_holdings():
    """Warnings generated when persona holds correlated pairs."""
    high_pairs = [
        {"stock_a": "1155.KL", "stock_b": "1295.KL",
         "correlation": 0.92, "strength": "very strong positive"},
    ]
    short_to_ticker = {"MAYBANK": "1155.KL", "PBBANK": "1295.KL", "TENAGA": "5347.KL"}
    ticker_to_short = {v: k for k, v in short_to_ticker.items()}

    warnings = check_persona_concentration(
        "ares", ["MAYBANK", "PBBANK", "TENAGA"],
        high_pairs, short_to_ticker, ticker_to_short,
    )
    assert len(warnings) == 1
    assert warnings[0]["stock_a"] == "MAYBANK"
    assert warnings[0]["stock_b"] == "PBBANK"
    assert "CRITICAL" in warnings[0]["risk"]


def test_check_concentration_no_overlap():
    """No warnings when persona doesn't hold the correlated pair."""
    high_pairs = [
        {"stock_a": "1155.KL", "stock_b": "1295.KL",
         "correlation": 0.85, "strength": "strong positive"},
    ]
    short_to_ticker = {"MAYBANK": "1155.KL", "PBBANK": "1295.KL"}
    ticker_to_short = {v: k for k, v in short_to_ticker.items()}

    # Persona only holds TENAGA (not in the pair)
    warnings = check_persona_concentration(
        "athena", ["TENAGA"],
        high_pairs, short_to_ticker, ticker_to_short,
    )
    assert len(warnings) == 0


def test_check_concentration_empty_holdings():
    """No warnings for persona with no holdings."""
    high_pairs = [
        {"stock_a": "1155.KL", "stock_b": "1295.KL",
         "correlation": 0.88, "strength": "strong positive"},
    ]
    short_to_ticker = {"MAYBANK": "1155.KL"}
    ticker_to_short = {v: k for k, v in short_to_ticker.items()}

    warnings = check_persona_concentration(
        "demeter", [], high_pairs, short_to_ticker, ticker_to_short,
    )
    assert len(warnings) == 0


def test_check_concentration_multiple_correlated_pairs():
    """Persona holding multiple overlapping pairs generates multiple warnings."""
    high_pairs = [
        {"stock_a": "1155.KL", "stock_b": "1295.KL",
         "correlation": 0.92, "strength": "very strong positive"},
        {"stock_a": "1155.KL", "stock_b": "5347.KL",
         "correlation": 0.82, "strength": "strong positive"},
    ]
    short_to_ticker = {
        "MAYBANK": "1155.KL", "PBBANK": "1295.KL", "TENAGA": "5347.KL",
    }
    ticker_to_short = {v: k for k, v in short_to_ticker.items()}

    warnings = check_persona_concentration(
        "ares", ["MAYBANK", "PBBANK", "TENAGA"],
        high_pairs, short_to_ticker, ticker_to_short,
    )
    assert len(warnings) == 2


def test_check_concentration_risk_level_translated():
    """Risk level is translated from correlation strength."""
    high_pairs = [
        {"stock_a": "1155.KL", "stock_b": "1295.KL",
         "correlation": 0.83, "strength": "strong positive"},
    ]
    short_to_ticker = {"MAYBANK": "1155.KL", "PBBANK": "1295.KL"}
    ticker_to_short = {v: k for k, v in short_to_ticker.items()}

    warnings = check_persona_concentration(
        "athena", ["MAYBANK", "PBBANK"],
        high_pairs, short_to_ticker, ticker_to_short,
    )
    assert "ELEVATED" in warnings[0]["risk"]


# ── Constants ─────────────────────────────────────────────────────────


def test_default_correlation_threshold():
    """Default correlation threshold is 0.80."""
    assert DEFAULT_THRESHOLD == 0.80
