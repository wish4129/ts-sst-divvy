"""Tests for kelly.py — Kelly criterion position sizing."""

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from risk.kelly import (
    compute_kelly_fraction,
    _kelly_label,
    MAX_KELLY_FRACTION,
)

# ── compute_kelly_fraction ──────────────────────────────────────────

def make_returns(wins: int, losses: int, avg_win: float = 0.02, avg_loss: float = 0.01) -> np.ndarray:
    """Build a synthetic returns array with known win/loss pattern."""
    rets = []
    for _ in range(wins):
        rets.append(avg_win)
    for _ in range(losses):
        rets.append(-avg_loss)
    return np.array(rets)


def test_kelly_balanced_50_50():
    """50% win rate, win/loss = 2.0 → positive Kelly."""
    rets = make_returns(100, 100, avg_win=0.02, avg_loss=0.01)
    f_star, win_rate, wl_ratio, edge = compute_kelly_fraction(rets)
    # p=0.5, b=2.0: f* = (2*0.5 - 0.5)/2 = 0.25
    assert win_rate == 0.5
    assert abs(wl_ratio - 2.0) < 0.01
    # Half-Kelly: 0.25/2 = 0.125
    assert 0.12 < f_star < 0.13  # ~0.125

def test_kelly_full_vs_half():
    """Full Kelly is double half-Kelly (before cap)."""
    rets = make_returns(100, 100, avg_win=0.02, avg_loss=0.01)
    f_half, _, _, _ = compute_kelly_fraction(rets, half_kelly=True)
    f_full, _, _, _ = compute_kelly_fraction(rets, half_kelly=False)
    assert abs(f_full - f_half * 2) < 0.001

def test_kelly_strong_edge():
    """70% win rate, 3:1 win/loss → high Kelly."""
    rets = make_returns(140, 60, avg_win=0.03, avg_loss=0.01)
    f_star, win_rate, wl_ratio, edge = compute_kelly_fraction(rets)
    assert win_rate == 0.7
    assert wl_ratio > 2.5
    assert f_star > 0.15  # strong edge

def test_kelly_capped_at_max():
    """Kelly fraction capped at MAX_KELLY_FRACTION (0.25)."""
    # Very high edge scenario
    rets = make_returns(180, 20, avg_win=0.05, avg_loss=0.005)
    f_star, _, _, _ = compute_kelly_fraction(rets, half_kelly=False)
    assert f_star <= MAX_KELLY_FRACTION

def test_kelly_all_wins():
    """100% win rate → no losses → returns 0 (can't compute W/L)."""
    rets = np.array([0.01] * 100)
    f_star, win_rate, wl_ratio, edge = compute_kelly_fraction(rets)
    # Early return: no losses → all values 0
    assert f_star == 0.0
    assert win_rate == 0.0
    assert wl_ratio == 0.0

def test_kelly_all_losses():
    """0% win rate → no wins → returns 0."""
    rets = np.array([-0.01] * 100)
    f_star, win_rate, wl_ratio, edge = compute_kelly_fraction(rets)
    assert win_rate == 0.0
    assert f_star == 0.0

def test_kelly_no_edge():
    """Win rate too low for positive Kelly."""
    # p=0.3, b=2.0: f* = (2*0.3 - 0.7)/2 = -0.05 → 0
    rets = make_returns(60, 140, avg_win=0.02, avg_loss=0.01)
    f_star, win_rate, wl_ratio, edge = compute_kelly_fraction(rets)
    assert win_rate == 0.3
    assert f_star == 0.0
    assert edge < 0  # negative edge

def test_kelly_negative_edge():
    """Negative edge produces zero Kelly."""
    rets = make_returns(30, 170, avg_win=0.01, avg_loss=0.02)
    f_star, _, _, edge = compute_kelly_fraction(rets)
    assert f_star == 0.0
    assert edge < 0

def test_kelly_too_few_samples():
    """Less than 20 returns → returns all zeros."""
    rets = np.array([0.01, -0.005] * 5)  # 10 samples
    f_star, win_rate, wl_ratio, edge = compute_kelly_fraction(rets)
    assert len(rets) < 20
    assert f_star == 0.0
    assert win_rate == 0.0

def test_kelly_zero_avg_loss():
    """Zero average loss handled gracefully."""
    rets = np.array([0.01] * 50 + [0.0] * 50)  # all non-negative
    f_star, _, _, _ = compute_kelly_fraction(rets)
    # Either no losses (all wins) or avg_loss = 0
    assert f_star == 0.0

def test_kelly_single_data_point():
    """Single return → too few samples."""
    rets = np.array([0.01])
    f_star, _, _, _ = compute_kelly_fraction(rets)
    assert f_star == 0.0

def test_kelly_edge_calculation():
    """Edge = (b*p - q) * 100."""
    rets = make_returns(100, 100, avg_win=0.02, avg_loss=0.01)
    _, _, _, edge = compute_kelly_fraction(rets, half_kelly=False)
    # b=2.0, p=0.5, q=0.5: edge = (2*0.5 - 0.5) * 100 = 50
    assert abs(edge - 50.0) < 1.0


# ── _kelly_label ────────────────────────────────────────────────────

def test_kelly_label_heavy():
    """f* >= 0.20 → Heavy allocation."""
    assert "Heavy" in _kelly_label(0.25)
    assert "Heavy" in _kelly_label(0.20)

def test_kelly_label_standard():
    """0.10 <= f* < 0.20 → Standard."""
    assert "Standard" in _kelly_label(0.15)
    assert "Standard" in _kelly_label(0.10)

def test_kelly_label_moderate():
    """0.05 <= f* < 0.10 → Moderate."""
    assert "Moderate" in _kelly_label(0.07)
    assert "Moderate" in _kelly_label(0.05)

def test_kelly_label_small():
    """0 < f* < 0.05 → Small position."""
    assert "Small" in _kelly_label(0.03)
    assert "Small" in _kelly_label(0.001)

def test_kelly_label_no_edge():
    """f* == 0 → No edge."""
    assert "No edge" in _kelly_label(0)
    assert "No edge" in _kelly_label(-0.1)
