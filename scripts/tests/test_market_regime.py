"""Tests for market_regime.py — bull/bear/sideways detection from price data."""

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from risk.market_regime import (
    compute_daily_returns,
    detect_regime,
    _ares_implication,
    _demeter_implication,
    _athena_implication,
    BULL_MA_PERIOD,
    BEAR_MA_PERIOD,
    VOLATILITY_HIGH,
    MOMENTUM_STRONG,
    MOMENTUM_WEAK,
)


def make_klci_data(
    closes: list,
    latest: float = None,
    ma_50: float = None,
    ma_200: float = None,
) -> dict:
    """Build KLCI data dict for detect_regime."""
    arr = closes if isinstance(closes, list) else list(closes)
    return {
        "closes": arr,
        "latest": latest if latest is not None else arr[-1],
        "ma_50": ma_50 if ma_50 is not None else float(np.mean(arr[-BULL_MA_PERIOD:])),
        "ma_200": ma_200 if ma_200 is not None else float(np.mean(arr[-min(BEAR_MA_PERIOD, len(arr)):])),
        "n_days": len(arr),
        "high_50d": float(np.max(arr[-BULL_MA_PERIOD:])),
        "low_50d": float(np.min(arr[-BULL_MA_PERIOD:])),
    }


# ── compute_daily_returns ──────────────────────────────────────────

def test_compute_daily_returns_basic():
    """Daily returns from simple price series."""
    closes = [100.0, 101.0, 102.0, 101.0]
    rets = compute_daily_returns(closes)
    assert len(rets) == 3
    assert abs(rets[0] - 0.01) < 1e-6   # 1%
    assert abs(rets[1] - 0.0099) < 1e-3  # ~0.99%
    assert rets[2] < 0                   # down day

def test_compute_daily_returns_flat():
    """Flat price series → zero returns."""
    closes = [100.0] * 10
    rets = compute_daily_returns(closes)
    assert np.allclose(rets, 0)


# ── detect_regime — BULL ───────────────────────────────────────────

def test_strong_bull_regime():
    """Price above both MAs + strong momentum → BULL, high confidence."""
    # Build 250 days of uptrend: starts at 1400, ends at 1650
    closes = list(np.linspace(1400, 1650, 250))
    data = make_klci_data(closes)
    # Artificially set MAs below price so above_ma50/above_ma200 = True
    data["ma_50"] = 1550
    data["ma_200"] = 1500
    data["latest"] = 1650
    result = detect_regime(data)
    assert result["regime"] == "BULL"
    assert result["confidence"] > 0.5

def test_moderate_bull_regime():
    """Above both MAs but weak momentum → BULL, moderate confidence."""
    closes = list(np.linspace(1500, 1550, 250))
    data = make_klci_data(closes)
    data["ma_50"] = 1520
    data["ma_200"] = 1480
    data["latest"] = 1550
    # Momentum < MOMENTUM_STRONG → moderate bull
    result = detect_regime(data)
    assert result["regime"] == "BULL"
    assert result["confidence"] == 0.6


# ── detect_regime — BEAR ───────────────────────────────────────────

def test_bear_regime_below_ma200():
    """Below 200-day MA + negative momentum → BEAR."""
    closes = list(np.linspace(1600, 1400, 300))
    data = make_klci_data(closes)
    data["ma_50"] = 1500
    data["ma_200"] = 1550  # price below ma_200
    data["latest"] = 1400
    result = detect_regime(data)
    assert result["regime"] == "BEAR"

def test_bear_regime_weak_trend():
    """Below 50MA, above 200MA, not pullback → BEAR fallback."""
    closes = list(np.linspace(1550, 1480, 250))
    data = make_klci_data(closes)
    data["ma_50"] = 1520
    data["ma_200"] = 1450
    data["latest"] = 1480  # below MA50, above MA200
    # Not a pullback (because not above_ma50 && above_ma200)
    result = detect_regime(data)
    assert result["regime"] in ("BEAR", "SIDEWAYS")


# ── detect_regime — SIDEWAYS ────────────────────────────────────────

def test_sideways_low_momentum():
    """Low absolute momentum → SIDEWAYS."""
    closes = list(np.linspace(1500, 1510, 250))
    data = make_klci_data(closes)
    data["ma_50"] = 1520
    data["ma_200"] = 1480
    data["latest"] = 1505
    # abs(momentum) < MOMENTUM_WEAK
    result = detect_regime(data)
    assert result["regime"] == "SIDEWAYS"

def test_sideways_pullback():
    """Below MA50, above MA200 → pullback SIDEWAYS."""
    closes = list(np.linspace(1550, 1520, 250))
    data = make_klci_data(closes)
    data["ma_50"] = 1540
    data["ma_200"] = 1500
    data["latest"] = 1520  # below MA50, above MA200
    result = detect_regime(data)
    assert result["regime"] == "SIDEWAYS"


# ── detect_regime — volatility overlay ──────────────────────────────

def test_high_volatility_overlay():
    """High volatility reduces position_multiplier."""
    # Generate volatile price series
    np.random.seed(42)
    base = np.linspace(1500, 1550, 250)
    noise = np.random.normal(0, 30, 250)
    closes = (base + noise).tolist()
    data = make_klci_data(closes)
    data["ma_50"] = 1480
    data["ma_200"] = 1450
    data["latest"] = closes[-1]
    result = detect_regime(data)
    # Position multiplier should be reduced due to volatility
    assert result["signals"]["volatility_regime"] in ("HIGH", "ELEVATED", "NORMAL")
    if result["signals"]["volatility_regime"] == "HIGH":
        assert result["position_multiplier"] < 1.0

def test_low_volatility_no_penalty():
    """Stable prices → NORMAL volatility, no extra reduction."""
    closes = list(np.linspace(1500, 1550, 250))
    data = make_klci_data(closes)
    data["ma_50"] = 1480
    data["ma_200"] = 1450
    data["latest"] = 1550
    result = detect_regime(data)
    assert result["signals"]["volatility_regime"] == "NORMAL"


# ── detect_regime — structure checks ───────────────────────────────

def test_regime_returns_all_fields():
    """detect_regime returns complete dict with all expected keys."""
    closes = list(np.linspace(1500, 1550, 250))
    data = make_klci_data(closes)
    data["ma_50"] = 1480
    data["ma_200"] = 1450
    data["latest"] = 1550
    result = detect_regime(data)
    assert "regime" in result
    assert "confidence" in result
    assert "description" in result
    assert "position_multiplier" in result
    assert "signals" in result
    assert "strategy_implications" in result
    assert "klci_latest" in result["signals"]
    assert "ma_50" in result["signals"]
    assert "ma_200" in result["signals"]
    assert "ma_crossover" in result["signals"]

def test_ma_crossover_detection():
    """MA50 > MA200 = golden cross."""
    closes = list(np.linspace(1500, 1550, 250))
    data = make_klci_data(closes)
    data["ma_50"] = 1550
    data["ma_200"] = 1500
    data["latest"] = 1550
    result = detect_regime(data)
    assert result["signals"]["ma_crossover"] == "golden"

def test_ma_death_cross():
    """MA50 < MA200 = death cross."""
    closes = list(np.linspace(1500, 1450, 250))
    data = make_klci_data(closes)
    data["ma_50"] = 1470
    data["ma_200"] = 1500
    data["latest"] = 1450
    result = detect_regime(data)
    assert result["signals"]["ma_crossover"] == "death"

def test_short_history_no_crash():
    """Only 60 data points — still returns valid regime."""
    closes = list(np.linspace(1500, 1550, 60))
    data = make_klci_data(closes)
    result = detect_regime(data)
    assert result["regime"] in ("BULL", "BEAR", "SIDEWAYS")


# ── Strategy implications ───────────────────────────────────────────

def test_ares_bull_implication():
    imp = _ares_implication("BULL", 0.15)
    assert "momentum" in imp.lower()

def test_ares_bear_implication():
    imp = _ares_implication("BEAR", 0.15)
    assert "defensive" in imp.lower()

def test_demeter_bear_implication():
    imp = _demeter_implication("BEAR")
    assert "20%" in imp or "buffer" in imp.lower()

def test_demeter_bull_implication():
    imp = _demeter_implication("BULL")
    assert "deploy" in imp.lower() or "5%" in imp

def test_athena_bull_implication():
    imp = _athena_implication("BULL", 0.15)
    assert "30%" in imp

def test_athena_bear_implication():
    imp = _athena_implication("BEAR", 0.15)
    assert "15%" in imp
