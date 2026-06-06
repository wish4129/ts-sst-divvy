#!/usr/bin/env python3
"""Market regime detection — classify Bursa conditions for strategy adaptation.

Detects bull/bear/sideways regimes using FBMKLCI (^KLSE) and sector indices.
Outputs regime classification that persona strategies can use to adjust
position sizing and entry aggressiveness.

Regimes:
  BULL    — KLCI above 50-day MA and rising, volatility low
  BEAR    — KLCI below 200-day MA or declining rapidly
  SIDEWAYS — Between MAs, range-bound, low momentum
  VOLATILE — High VIX-like volatility regardless of direction

Usage:
  cd ~/xiongit/divvy && .venv/bin/python3 scripts/risk/market_regime.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    import yfinance as yf
except ImportError:
    import os
    os.system(f"{sys.executable} -m pip install yfinance --quiet")
    import yfinance as yf

ROOT = Path(__file__).resolve().parent.parent.parent
MALAYSIA_TZ = timezone(timedelta(hours=8))

# Regime thresholds
BULL_MA_PERIOD = 50
BEAR_MA_PERIOD = 200
VOLATILITY_HIGH = 0.25  # Annualized vol > 25% = volatile regime
MOMENTUM_STRONG = 10.0   # % change over 50 days for strong trend
MOMENTUM_WEAK = 3.0      # % change threshold for sideways


def fetch_klci_data(years: float = 3.0) -> Optional[Dict]:
    """Fetch FBMKLCI historical data.

    Returns dict with closes, dates, and computed MAs.
    """
    end = datetime.now()
    start = end - timedelta(days=int(years * 365) + 30)

    try:
        # Use Ticker object for index data (more reliable)
        ticker = yf.Ticker("^KLSE")
        hist = ticker.history(start=start.strftime("%Y-%m-%d"),
                              end=end.strftime("%Y-%m-%d"),
                              auto_adjust=True)
        if hist is None or hist.empty:
            return None

        closes = hist["Close"].values
        # Force to Python float list, handling numpy scalars
        closes = [float(x) for x in closes if not np.isnan(x)]
        if len(closes) < BULL_MA_PERIOD:
            return None

        return {
            "closes": closes,
            "latest": closes[-1],
            "ma_50": float(np.mean(closes[-BULL_MA_PERIOD:])),
            "ma_200": float(np.mean(closes[-min(BEAR_MA_PERIOD, len(closes)):])),
            "n_days": len(closes),
            "high_50d": float(np.max(closes[-BULL_MA_PERIOD:])),
            "low_50d": float(np.min(closes[-BULL_MA_PERIOD:])),
        }
    except Exception as e:
        print(f"  ⚠ KLCI fetch failed: {e}")
        return None


def compute_daily_returns(closes: List[float]) -> np.ndarray:
    """Daily returns from close prices."""
    arr = np.array(closes)
    return (arr[1:] - arr[:-1]) / arr[:-1]


def detect_regime(klci_data: Dict) -> Dict:
    """Classify current market regime from KLCI data.

    Returns dict with regime, confidence, and sub-signals.
    """
    closes = klci_data["closes"]
    latest = klci_data["latest"]
    ma_50 = klci_data["ma_50"]
    ma_200 = klci_data["ma_200"]

    # Compute signals
    above_ma50 = latest > ma_50
    above_ma200 = latest > ma_200

    # 50-day momentum
    if len(closes) >= BULL_MA_PERIOD:
        mom_50d = (latest - closes[-BULL_MA_PERIOD]) / closes[-BULL_MA_PERIOD] * 100
    else:
        mom_50d = 0

    # 200-day momentum
    if len(closes) >= BEAR_MA_PERIOD:
        mom_200d = (latest - closes[-BEAR_MA_PERIOD]) / closes[-BEAR_MA_PERIOD] * 100
    else:
        mom_200d = 0

    # Volatility (annualized)
    returns = compute_daily_returns(closes)
    if len(returns) > 20:
        vol_20d = float(np.std(returns[-20:]) * np.sqrt(252))
    else:
        vol_20d = 0

    # MA crossover (golden cross / death cross)
    ma_cross = "golden" if ma_50 > ma_200 else "death"

    # Determine regime
    if above_ma50 and above_ma200 and mom_50d > MOMENTUM_STRONG:
        regime = "BULL"
        confidence = min(0.9, 0.5 + mom_50d / 30)
        description = "Strong uptrend — aggressive entries favored"
        position_multiplier = 1.2  # Increase position sizes
    elif above_ma50 and above_ma200:
        regime = "BULL"
        confidence = 0.6
        description = "Moderate uptrend — standard entries"
        position_multiplier = 1.0
    elif not above_ma200 and mom_200d < -MOMENTUM_WEAK:
        regime = "BEAR"
        confidence = min(0.9, 0.5 + abs(mom_200d) / 30)
        description = "Downtrend — defensive positioning, tight stops"
        position_multiplier = 0.5  # Halve position sizes
    elif not above_ma50 and above_ma200:
        regime = "SIDEWAYS"
        confidence = 0.5
        description = "Pullback in uptrend — cautious entries"
        position_multiplier = 0.8
    elif abs(mom_50d) < MOMENTUM_WEAK:
        regime = "SIDEWAYS"
        confidence = 0.7
        description = "Range-bound — neutral positioning"
        position_multiplier = 1.0
    else:
        regime = "BEAR"
        confidence = 0.5
        description = "Weak trend — reduce exposure"
        position_multiplier = 0.7

    # Volatility overlay
    if vol_20d > VOLATILITY_HIGH:
        volatility_regime = "HIGH"
        position_multiplier *= 0.7  # Reduce further in high vol
        description += " (high volatility — reduced sizing)"
    elif vol_20d > 0.18:
        volatility_regime = "ELEVATED"
        position_multiplier *= 0.85
    else:
        volatility_regime = "NORMAL"

    return {
        "regime": regime,
        "confidence": round(confidence, 2),
        "description": description,
        "position_multiplier": round(position_multiplier, 2),
        "signals": {
            "klci_latest": round(latest, 2),
            "ma_50": round(ma_50, 2),
            "ma_200": round(ma_200, 2),
            "above_ma50": above_ma50,
            "above_ma200": above_ma200,
            "momentum_50d_pct": round(mom_50d, 2),
            "momentum_200d_pct": round(mom_200d, 2),
            "volatility_20d_annualized_pct": round(vol_20d * 100, 1),
            "ma_crossover": ma_cross,
            "volatility_regime": volatility_regime,
        },
        "strategy_implications": {
            "ares": _ares_implication(regime, vol_20d),
            "demeter": _demeter_implication(regime),
            "athena": _athena_implication(regime, vol_20d),
        },
    }


def _ares_implication(regime: str, vol: float) -> str:
    """Strategy guidance for Ares (aggressive momentum)."""
    if regime == "BULL":
        return "Full momentum — trailing stops at 15%, no cooling trims"
    elif regime == "BEAR":
        return "Defensive — tight trailing stops at 10%, reduce exposure"
    elif regime == "SIDEWAYS":
        return "Selective — only enter on strong volume confirmation"
    return "Standard momentum rules"


def _demeter_implication(regime: str) -> str:
    """Strategy guidance for Demeter (dividend conservative)."""
    if regime == "BULL":
        return "Deploy cash buffer to 5%, favor growth dividends"
    elif regime == "BEAR":
        return "Increase cash buffer to 20%, accumulate defensive REITs"
    elif regime == "SIDEWAYS":
        return "Maintain 10% buffer, reinvest dividends"
    return "Standard dividend rules"


def _athena_implication(regime: str, vol: float) -> str:
    """Strategy guidance for Athena (GARP balanced)."""
    if regime == "BULL":
        return "Take profit at 30% (not 25%), dip buy at -8%"
    elif regime == "BEAR":
        return "Take profit at 15%, tight stop at -7%, no dip buys"
    elif regime == "SIDEWAYS":
        return "Standard GARP — take profit 25%, dip buy -10%"
    return "Standard GARP rules"


def get_regime_multiplier() -> float:
    """Get current recommended position size multiplier (quick access)."""
    klci = fetch_klci_data(years=3.0)
    if klci is None:
        return 1.0
    regime = detect_regime(klci)
    return regime["position_multiplier"]


# ── Main ────────────────────────────────────────────────────────────

def main():
    print(f"\n{'='*60}")
    print("Market Regime Detection — FBMKLCI Analysis")
    print(f"{'='*60}")

    klci = fetch_klci_data(years=3.0)
    if klci is None:
        print("  ERROR: Could not fetch KLCI data")
        sys.exit(1)

    regime = detect_regime(klci)
    signals = regime["signals"]

    # Display
    emoji = {"BULL": "🐂", "BEAR": "🐻", "SIDEWAYS": "↔️"}
    print(f"\n  Regime: {emoji.get(regime['regime'], '❓')} {regime['regime']} "
          f"(confidence: {regime['confidence']:.0%})")
    print(f"  {regime['description']}")
    print(f"  Position multiplier: {regime['position_multiplier']:.2f}x")
    print(f"\n  KLCI: {signals['klci_latest']:.2f}")
    print(f"  50-day MA: {signals['ma_50']:.2f}  {'▲ above' if signals['above_ma50'] else '▼ below'}")
    print(f"  200-day MA: {signals['ma_200']:.2f}  {'▲ above' if signals['above_ma200'] else '▼ below'}")
    print(f"  50d momentum: {signals['momentum_50d_pct']:+.1f}%")
    print(f"  200d momentum: {signals['momentum_200d_pct']:+.1f}%")
    print(f"  20d volatility (ann): {signals['volatility_20d_annualized_pct']:.1f}%")
    print(f"  MA crossover: {signals['ma_crossover']}")

    print(f"\n  Strategy implications:")
    for pid, imp in regime["strategy_implications"].items():
        print(f"    {pid:8s}: {imp}")

    # Save
    output_path = ROOT / "data" / "market_regime.json"
    output = {
        "detected_at": datetime.now(MALAYSIA_TZ).isoformat(),
        **regime,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2))
    print(f"\n  ✓ Saved to {output_path}")


if __name__ == "__main__":
    main()
