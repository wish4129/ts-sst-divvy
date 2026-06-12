#!/usr/bin/env python3
"""Backtesting engine — replay persona strategies against 2 years of Bursa data.

Fetches historical daily prices via yfinance, replays each persona's
trading strategy day-by-day, and computes performance metrics.

Outputs:
  - CAGR, Sharpe ratio, max drawdown per persona
  - Trade log with entry/exit prices and PnL
  - Daily portfolio value time series
  - Comparison against buy-and-hold benchmark

Usage:
  cd ~/xiongit/divvy && .venv/bin/python3 scripts/backtest/engine.py
  cd ~/xiongit/divvy && .venv/bin/python3 scripts/backtest/engine.py --years 3
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db import get_db
from persona_db import (
    get_all_stocks_dict,
    TICKER_TO_SHORT,
    SHORT_TO_TICKER,
)
from backtest.metrics import (
    cagr,
    max_drawdown,
    sharpe_ratio,
    annualized_volatility,
    win_rate,
    profit_factor,
    total_return,
)

try:
    import yfinance as yf
except ImportError:
    import os
    os.system(f"{sys.executable} -m pip install yfinance --quiet")
    import yfinance as yf

ROOT = Path(__file__).resolve().parent.parent.parent
MALAYSIA_TZ = timezone(timedelta(hours=8))
LOT_SIZE = 100
INITIAL_CAPITAL = 10000.0

# ── Persona rules (mirrors portfolio_manager.py) ─────────────────────

PERSONA_RULES = {
    "ares": {
        "stop_loss": -0.12,
        "take_profit": None,
        "max_single_position": 0.25,
        "min_stocks": 4,
        "rebalance_drift": 0.07,
        "cash_buffer": 0.0,
        "momentum_cooling_threshold": -0.05,
        "momentum_cooling_trim": 0.25,
        "trailing_stop_loss": -0.15,
        "use_trailing_stop": True,
        "rsi_overbought": 70,
        "rsi_filter_entries": False,  # Disabled for backtest (no live RSI)
        "volume_confirmation_entries": False,  # Disabled for backtest
    },
    "demeter": {
        "stop_loss": None,
        "take_profit": None,
        "max_single_position": 0.35,
        "min_stocks": 4,
        "rebalance_drift": 0.10,
        "cash_buffer": 0.10,
        "fd_rate": 0.03,
        "min_dividend_yield": 0.03,
        "rsi_filter_entries": False,
        "volume_confirmation_entries": False,
    },
    "athena": {
        "stop_loss": -0.10,
        "take_profit": 0.25,
        "take_profit_sell_pct": 0.50,
        "max_single_position": 0.30,
        "min_stocks": 5,
        "rebalance_drift": 0.10,
        "dip_buy_threshold": -0.10,
        "dip_buy_pct": 0.50,
        "cash_buffer": 0.0,
        "full_exit_threshold": 0.40,
        "dip_buy_cooldown_days": 30,
        "rsi_filter_entries": False,
        "volume_confirmation_entries": False,
    },
}


def round_lot(shares: float) -> int:
    return (int(shares) // LOT_SIZE) * LOT_SIZE


# ── Data fetching ────────────────────────────────────────────────────

def fetch_historical_prices(
    tickers: List[str],
    years: float = 2.0,
) -> Dict[str, List[float]]:
    """Fetch daily close prices for a set of tickers.

    Returns {ticker: [close_prices]} where prices are chronological.
    All series are aligned to the same date index.
    """
    if not tickers:
        return {}

    end = datetime.now()
    start = end - timedelta(days=int(years * 365) + 30)

    print(f"  Fetching {len(tickers)} stocks from {start.date()} to {end.date()}...")
    data = yf.download(
        tickers,
        start=start.strftime("%Y-%m-%d"),
        end=end.strftime("%Y-%m-%d"),
        progress=False,
        auto_adjust=True,
    )

    if data.empty:
        print("  ⚠ yfinance returned empty data")
        return {}

    # Handle single ticker case (yfinance returns Series, not DataFrame)
    if len(tickers) == 1:
        close = data["Close"]
        if hasattr(close, "dropna"):
            prices = close.dropna().tolist()
            return {tickers[0]: prices}
        return {}

    close = data["Close"]
    result = {}
    for ticker in tickers:
        if ticker in close.columns:
            prices = close[ticker].dropna().tolist()
            if len(prices) >= 20:  # Need minimum data
                result[ticker] = prices
    return result


# ── Strategy engines (simplified for backtest) ───────────────────────

def compute_rsi_from_prices(prices: List[float], period: int = 14) -> Optional[float]:
    """Compute RSI-14 from a list of closing prices."""
    if len(prices) < period + 1:
        return None
    closes = prices
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def ares_backtest(
    holdings: Dict[str, dict],
    cash: float,
    prices: Dict[str, float],
    price_history: Dict[str, List[float]],
    rules: dict,
    day_index: int,
    prev_prices: Dict[str, float],
    initial_capital: float,
    high_water_marks: Dict[str, float],
) -> Tuple[Dict[str, dict], float, List[dict], Dict[str, float]]:
    """Ares backtest: trailing stop, momentum cooling, Kronos-style filtered rebalance."""
    trades = []
    new_holdings = {k: v.copy() for k, v in holdings.items()}
    new_cash = cash
    new_hwm = {**high_water_marks}

    for name, h in list(new_holdings.items()):
        current_price = prices.get(name, h["cost"])
        if current_price <= 0:
            continue

        # Update high water mark
        if name not in new_hwm:
            new_hwm[name] = current_price
        elif current_price > new_hwm[name]:
            new_hwm[name] = current_price

        peak = new_hwm[name]
        pnl_pct = (current_price - h["cost"]) / h["cost"] if h["cost"] > 0 else 0

        # Trailing stop
        if rules.get("use_trailing_stop"):
            trailing_pct = abs(rules.get("trailing_stop_loss", -0.15))
            drawdown = (current_price - peak) / peak if peak > 0 else 0
            if drawdown <= -trailing_pct:
                sell_shares = round_lot(h["shares"])
                if sell_shares >= LOT_SIZE:
                    proceeds = sell_shares * current_price
                    new_cash += proceeds
                    # Record trade with PnL
                    trade_pnl = (current_price - h["cost"]) * sell_shares
                    trades.append({
                        "action": "SELL_ALL", "stock": name, "shares": sell_shares,
                        "price": current_price, "pnl": round(trade_pnl, 2),
                        "reason": f"Trailing stop: {drawdown*100:.1f}% from peak",
                        "day": day_index,
                    })
                    del new_holdings[name]
                    del new_hwm[name]
                    continue

        # Fixed stop loss
        if rules.get("stop_loss") and pnl_pct <= rules["stop_loss"]:
            sell_shares = round_lot(h["shares"])
            if sell_shares >= LOT_SIZE:
                proceeds = sell_shares * current_price
                new_cash += proceeds
                trade_pnl = (current_price - h["cost"]) * sell_shares
                trades.append({
                    "action": "SELL_ALL", "stock": name, "shares": sell_shares,
                    "price": current_price, "pnl": round(trade_pnl, 2),
                    "reason": f"Stop loss ({pnl_pct*100:.1f}%)",
                    "day": day_index,
                })
                del new_holdings[name]
                del new_hwm[name]
                continue

        # Momentum cooling: trim if day-over-day drop > 5%
        if name in prev_prices and prev_prices[name] > 0:
            session_change = (current_price - prev_prices[name]) / prev_prices[name]
            if session_change <= rules.get("momentum_cooling_threshold", -0.05):
                trim_pct = rules.get("momentum_cooling_trim", 0.25)
                trim_shares = round_lot(h["shares"] * trim_pct)
                if trim_shares >= LOT_SIZE:
                    proceeds = trim_shares * current_price
                    new_cash += proceeds
                    trade_pnl = (current_price - h["cost"]) * trim_shares
                    trades.append({
                        "action": "SELL", "stock": name, "shares": trim_shares,
                        "price": current_price, "pnl": round(trade_pnl, 2),
                        "reason": f"Momentum cool {session_change*100:.1f}%",
                        "day": day_index,
                    })
                    new_holdings[name]["shares"] -= trim_shares
                    if new_holdings[name]["shares"] <= 0:
                        del new_holdings[name]

    # Rebalance: drift-based adjustments
    triggered = {t["stock"] for t in trades if t["action"] == "SELL_ALL"}
    total_value = sum(
        new_holdings[n]["shares"] * prices.get(n, new_holdings[n]["cost"])
        for n in new_holdings
    ) + new_cash

    for name in list(new_holdings.keys()):
        if name in triggered:
            continue
        h = new_holdings[name]
        current_price = prices.get(name, h["cost"])
        current_value = h["shares"] * current_price
        weight = current_value / total_value if total_value > 0 else 0
        target_pct = h.get("target_pct", 0) / 100 if isinstance(h.get("target_pct"), (int, float)) and h.get("target_pct", 0) > 1 else 0.15
        drift = abs(weight - target_pct)

        if drift > rules.get("rebalance_drift", 0.07):
            if weight < target_pct:
                # BUY
                target_value = total_value * target_pct
                buy_amount = min(new_cash * 0.5, (target_value - current_value) * 0.5)
                if buy_amount > 0 and current_price > 0:
                    buy_shares = round_lot(buy_amount / current_price)
                    if buy_shares >= LOT_SIZE:
                        cost = buy_shares * current_price
                        if cost <= new_cash:
                            new_cash -= cost
                            h["cost"] = ((h["cost"] * h["shares"]) + cost) / (h["shares"] + buy_shares)
                            h["shares"] += buy_shares
                            trades.append({
                                "action": "BUY", "stock": name, "shares": buy_shares,
                                "price": current_price, "pnl": 0,
                                "reason": f"Rebalance +{drift*100:.1f}% drift",
                                "day": day_index,
                            })
            elif weight > target_pct:
                # SELL (trim to target)
                excess_value = current_value - (total_value * target_pct)
                if excess_value > 0 and current_price > 0:
                    sell_shares = round_lot(excess_value / current_price)
                    if sell_shares >= LOT_SIZE and sell_shares < h["shares"]:
                        proceeds = sell_shares * current_price
                        new_cash += proceeds
                        trade_pnl = (current_price - h["cost"]) * sell_shares
                        trades.append({
                            "action": "SELL", "stock": name, "shares": sell_shares,
                            "price": current_price, "pnl": round(trade_pnl, 2),
                            "reason": f"Rebalance -{drift*100:.1f}% drift",
                            "day": day_index,
                        })
                        h["shares"] -= sell_shares

    return new_holdings, new_cash, trades, new_hwm


def demeter_backtest(
    holdings: Dict[str, dict],
    cash: float,
    prices: Dict[str, float],
    price_history: Dict[str, List[float]],
    rules: dict,
    day_index: int,
    initial_capital: float,
) -> Tuple[Dict[str, dict], float, List[dict]]:
    """Demeter backtest: cash buffer enforcement, DY compression sell."""
    trades = []
    new_holdings = {k: v.copy() for k, v in holdings.items()}
    new_cash = cash

    total_value = sum(
        new_holdings[n]["shares"] * prices.get(n, new_holdings[n]["cost"])
        for n in new_holdings
    ) + new_cash

    cash_pct = new_cash / total_value if total_value > 0 else 0
    cash_buffer = rules.get("cash_buffer", 0.10)

    # Deploy excess cash into most underweight holding
    if cash_pct > cash_buffer + 0.05:
        best_name, best_score = None, -999
        for name, h in new_holdings.items():
            current_price = prices.get(name, h["cost"])
            current_value = h["shares"] * current_price
            weight = current_value / total_value if total_value > 0 else 0
            target_pct = h.get("target_pct", 0) / 100 if isinstance(h.get("target_pct"), (int, float)) and h.get("target_pct", 0) > 1 else 0.15
            under = target_pct - weight
            if under <= 0:
                continue
            score = under
            if score > best_score:
                best_score = score
                best_name = name

        if best_name and best_score > rules.get("rebalance_drift", 0.10):
            excess = total_value * (cash_pct - cash_buffer) * 0.5
            current_price = prices.get(best_name, new_holdings[best_name]["cost"])
            if current_price > 0:
                buy_shares = round_lot(excess / current_price)
                if buy_shares >= LOT_SIZE:
                    cost = buy_shares * current_price
                    if cost <= new_cash:
                        new_cash -= cost
                        h = new_holdings[best_name]
                        h["cost"] = ((h["cost"] * h["shares"]) + cost) / (h["shares"] + buy_shares)
                        h["shares"] += buy_shares
                        trades.append({
                            "action": "BUY", "stock": best_name, "shares": buy_shares,
                            "price": current_price, "pnl": 0,
                            "reason": f"Deploy excess cash ({cash_pct*100:.1f}% > {cash_buffer*100:.0f}%)",
                            "day": day_index,
                        })

    # DY compression: sell if price +67% from initial
    for name, h in list(new_holdings.items()):
        current_price = prices.get(name, h["cost"])
        initial_price = h.get("initial_price", h["cost"])
        if initial_price > 0 and current_price >= initial_price * 1.67:
            sell_shares = round_lot(h["shares"] * 0.5)
            if sell_shares >= LOT_SIZE:
                proceeds = sell_shares * current_price
                new_cash += proceeds
                trade_pnl = (current_price - h["cost"]) * sell_shares
                trades.append({
                    "action": "SELL", "stock": name, "shares": sell_shares,
                    "price": current_price, "pnl": round(trade_pnl, 2),
                    "reason": f"DY compression: +{(current_price/initial_price-1)*100:.0f}%",
                    "day": day_index,
                })
                h["shares"] -= sell_shares
                if h["shares"] <= 0:
                    del new_holdings[name]

    return new_holdings, new_cash, trades


def athena_backtest(
    holdings: Dict[str, dict],
    cash: float,
    prices: Dict[str, float],
    price_history: Dict[str, List[float]],
    rules: dict,
    day_index: int,
    initial_capital: float,
) -> Tuple[Dict[str, dict], float, List[dict]]:
    """Athena backtest: take profit, full exit, stop loss, dip buy, rebalance."""
    trades = []
    new_holdings = {k: v.copy() for k, v in holdings.items()}
    new_cash = cash

    for name, h in list(new_holdings.items()):
        current_price = prices.get(name, h["cost"])
        if current_price <= 0:
            continue

        pnl_pct = (current_price - h["cost"]) / h["cost"] if h["cost"] > 0 else 0

        # Full exit at +40%
        full_exit = rules.get("full_exit_threshold", 0.40)
        if full_exit and pnl_pct >= full_exit:
            sell_shares = round_lot(h["shares"])
            if sell_shares >= LOT_SIZE:
                proceeds = sell_shares * current_price
                new_cash += proceeds
                trade_pnl = (current_price - h["cost"]) * sell_shares
                trades.append({
                    "action": "SELL_ALL", "stock": name, "shares": sell_shares,
                    "price": current_price, "pnl": round(trade_pnl, 2),
                    "reason": f"Full exit +{pnl_pct*100:.1f}%",
                    "day": day_index,
                })
                del new_holdings[name]
                continue

        # Take profit at +25%
        if rules.get("take_profit") and pnl_pct >= rules["take_profit"]:
            sell_pct = rules.get("take_profit_sell_pct", 0.50)
            sell_shares = round_lot(h["shares"] * sell_pct)
            if sell_shares >= LOT_SIZE:
                proceeds = sell_shares * current_price
                new_cash += proceeds
                trade_pnl = (current_price - h["cost"]) * sell_shares
                trades.append({
                    "action": "SELL", "stock": name, "shares": sell_shares,
                    "price": current_price, "pnl": round(trade_pnl, 2),
                    "reason": f"Take profit +{pnl_pct*100:.1f}%",
                    "day": day_index,
                })
                h["shares"] -= sell_shares
                if h["shares"] <= 0:
                    del new_holdings[name]
                    continue

        # Stop loss at -10%
        if rules.get("stop_loss") and pnl_pct <= rules["stop_loss"]:
            sell_shares = round_lot(h["shares"])
            if sell_shares >= LOT_SIZE:
                proceeds = sell_shares * current_price
                new_cash += proceeds
                trade_pnl = (current_price - h["cost"]) * sell_shares
                trades.append({
                    "action": "SELL_ALL", "stock": name, "shares": sell_shares,
                    "price": current_price, "pnl": round(trade_pnl, 2),
                    "reason": f"Stop loss ({pnl_pct*100:.1f}%)",
                    "day": day_index,
                })
                del new_holdings[name]
                continue

        # Dip buy at -10%
        if rules.get("dip_buy_threshold") and pnl_pct <= rules["dip_buy_threshold"] and pnl_pct > (rules.get("stop_loss", -999)):
            buy_pct = rules.get("dip_buy_pct", 0.50)
            buy_shares = round_lot(h["shares"] * buy_pct)
            if buy_shares >= LOT_SIZE:
                cost = buy_shares * current_price
                if cost <= new_cash * 0.5:
                    new_cash -= cost
                    h["cost"] = ((h["cost"] * h["shares"]) + cost) / (h["shares"] + buy_shares)
                    h["shares"] += buy_shares
                    trades.append({
                        "action": "BUY", "stock": name, "shares": buy_shares,
                        "price": current_price, "pnl": 0,
                        "reason": f"Dip buy at {pnl_pct*100:.1f}%",
                        "day": day_index,
                    })

    # Rebalance drift
    triggered = {t["stock"] for t in trades if t["action"] == "SELL_ALL"}
    total_value = sum(
        new_holdings[n]["shares"] * prices.get(n, new_holdings[n]["cost"])
        for n in new_holdings
    ) + new_cash

    for name in list(new_holdings.keys()):
        if name in triggered:
            continue
        h = new_holdings[name]
        current_price = prices.get(name, h["cost"])
        current_value = h["shares"] * current_price
        weight = current_value / total_value if total_value > 0 else 0
        target_pct = h.get("target_pct", 0) / 100 if isinstance(h.get("target_pct"), (int, float)) and h.get("target_pct", 0) > 1 else 0.15
        drift = abs(weight - target_pct)

        if drift > rules.get("rebalance_drift", 0.10):
            if weight < target_pct:
                target_value = total_value * target_pct
                buy_amount = min(new_cash * 0.3, (target_value - current_value) * 0.3)
                if buy_amount > 0 and current_price > 0:
                    buy_shares = round_lot(buy_amount / current_price)
                    if buy_shares >= LOT_SIZE:
                        cost = buy_shares * current_price
                        if cost <= new_cash:
                            new_cash -= cost
                            h["cost"] = ((h["cost"] * h["shares"]) + cost) / (h["shares"] + buy_shares)
                            h["shares"] += buy_shares
                            trades.append({
                                "action": "BUY", "stock": name, "shares": buy_shares,
                                "price": current_price, "pnl": 0,
                                "reason": f"Rebalance +{drift*100:.1f}% drift",
                                "day": day_index,
                            })

    return new_holdings, new_cash, trades


STRATEGY_ENGINES = {
    "ares": ares_backtest,
    "demeter": demeter_backtest,
    "athena": athena_backtest,
}


# ── Portfolio valuation ─────────────────────────────────────────────

def portfolio_value(
    holdings: Dict[str, dict],
    cash: float,
    prices: Dict[str, float],
) -> float:
    """Total portfolio value: holdings at current prices + cash."""
    stock_value = sum(
        h["shares"] * prices.get(name, h["cost"])
        for name, h in holdings.items()
    )
    return stock_value + cash


def buy_and_hold_value(
    initial_holdings: Dict[str, dict],
    prices: Dict[str, float],
) -> float:
    """Value if holdings were never traded (buy and hold benchmark)."""
    return sum(
        h["shares"] * prices.get(name, h["cost"])
        for name, h in initial_holdings.items()
    )


# ── Main ────────────────────────────────────────────────────────────

def run_backtest(years: float = 2.0) -> dict:
    """Run backtest for all 3 persona strategies.

    Returns dict with results per persona.
    """
    print(f"\n{'='*60}")
    print(f"Divvy Backtesting Engine — {years} Year Backtest")
    print(f"{'='*60}")

    # Load current portfolio from DB
    db = get_db()
    cur = db.cursor()

    # Get all stocks with ticker codes
    all_stocks = get_all_stocks_dict()

    # Collect all tickers
    ticker_set = set()
    for info in all_stocks.values():
        ticker_set.add(info["code"])

    tickers = sorted(ticker_set)
    print(f"\n  Portfolio universe: {len(tickers)} stocks")

    # Fetch historical prices
    hist_prices = fetch_historical_prices(tickers, years)
    if not hist_prices:
        print("  ERROR: No historical data available")
        cur.close()
        db.close()
        return {}

    # Build unified price index (all tickers aligned by date)
    # Use the ticker with most data points as reference
    available_tickers = list(hist_prices.keys())
    print(f"  Available price data: {len(available_tickers)}/{len(tickers)} stocks")
    if not available_tickers:
        cur.close()
        db.close()
        return {}

    # Get ticker → short name mapping
    ticker_to_name = {}
    for short, info in all_stocks.items():
        ticker_to_name[info["code"]] = short

    # Load current persona portfolios from DB
    cur.execute("SELECT * FROM user_portfolios ORDER BY persona")
    portfolios_db = {r["persona"]: r for r in [dict(zip([c[0] for c in cur.description], row)) for row in cur.fetchall()]}

    # Get holdings for all personas
    cur.execute(
        """SELECT up.persona, ph.stock_id, ph.shares, ph.avg_cost, ph.target_pct,
                  s.initial_price
           FROM portfolio_holdings ph
           JOIN user_portfolios up ON up.id = ph.portfolio_id
           JOIN stocks s ON s.id = ph.stock_id
           WHERE ph.shares >= 100"""
    )
    persona_holdings_raw = {}
    for row in cur.fetchall():
        r = dict(zip([c[0] for c in cur.description], row))
        pid = r["persona"]
        if pid not in persona_holdings_raw:
            persona_holdings_raw[pid] = {}
        short = TICKER_TO_SHORT.get(r["stock_id"], r["stock_id"].replace(".KL", ""))
        persona_holdings_raw[pid][short] = {
            "shares": r["shares"],
            "cost": float(r["avg_cost"]),
            "target_pct": float(r["target_pct"]),
            "initial_price": float(r["initial_price"] or r["avg_cost"]),
        }

    cur.close()
    db.close()

    # Compute days in backtest
    ref_ticker = available_tickers[0]
    n_days = len(hist_prices[ref_ticker])
    actual_years = n_days / 252  # Trading days per year
    print(f"  Trading days: {n_days} ({actual_years:.1f} years)\n")

    results = {}

    for pid in ["ares", "demeter", "athena"]:
        if pid not in persona_holdings_raw:
            print(f"  [{pid}] No holdings — skipping")
            continue

        holdings = persona_holdings_raw[pid]
        rules = PERSONA_RULES[pid]
        initial_cap = float(portfolios_db.get(pid, {}).get("initial_capital", INITIAL_CAPITAL))

        # Calculate initial cash (capital - invested)
        invested = sum(h["shares"] * h["cost"] for h in holdings.values())
        cash = max(0, initial_cap - invested)

        # Initial portfolio value
        initial_prices = {
            name: hist_prices.get(SHORT_TO_TICKER.get(name, name + ".KL"), [h["cost"]])[0]
            if name in ticker_to_name and ticker_to_name.get(SHORT_TO_TICKER.get(name, "")) in hist_prices
            else h["cost"]
            for name, h in holdings.items()
        }
        initial_value = portfolio_value(holdings, cash, initial_prices)

        # Daily tracking
        daily_values = []
        all_trades = []
        high_water_marks = {}
        prev_day_prices: Dict[str, float] = {}  # Yesterday's prices for momentum cooling

        for day in range(n_days):
            # Build price snapshot for this day
            day_prices: Dict[str, float] = {}
            for ticker, price_series in hist_prices.items():
                if day < len(price_series):
                    short = ticker_to_name.get(ticker, ticker.replace(".KL", ""))
                    day_prices[short] = float(price_series[day])

            # Fill missing prices with cost basis (holdings still exist but no data)
            for name in holdings:
                if name not in day_prices:
                    day_prices[name] = holdings[name]["cost"]

            # Record daily value
            val = portfolio_value(holdings, cash, day_prices)
            daily_values.append(val)

            # Run strategy engine
            engine = STRATEGY_ENGINES.get(pid)
            if engine:
                if pid == "ares":
                    holdings, cash, day_trades, high_water_marks = engine(
                        holdings, cash, day_prices, hist_prices, rules,
                        day, prev_day_prices, initial_cap, high_water_marks,
                    )
                else:
                    holdings, cash, day_trades = engine(
                        holdings, cash, day_prices, hist_prices, rules,
                        day, initial_cap,
                    )

                # Enforce lot sizes on executions
                valid_trades = []
                for t in day_trades:
                    lot_shares = round_lot(t["shares"])
                    if lot_shares < LOT_SIZE:
                        continue
                    t["shares"] = lot_shares
                    valid_trades.append(t)
                all_trades.extend(valid_trades)

            # Save this day's prices as prev for next iteration's momentum cooling
            prev_day_prices = day_prices.copy()

        # Final value
        final_day = n_days - 1
        final_prices = {}
        for ticker, price_series in hist_prices.items():
            if final_day < len(price_series):
                short = ticker_to_name.get(ticker, ticker.replace(".KL", ""))
                final_prices[short] = float(price_series[final_day])

        final_value = portfolio_value(holdings, cash, final_prices)

        # Buy-and-hold benchmark
        bh_holdings = {k: v.copy() for k, v in persona_holdings_raw[pid].items()}
        bh_final = buy_and_hold_value(bh_holdings, final_prices)

        # Daily returns
        daily_returns = []
        for i in range(1, len(daily_values)):
            if daily_values[i - 1] > 0:
                daily_returns.append((daily_values[i] - daily_values[i - 1]) / daily_values[i - 1])

        # Metrics
        cagr_val = cagr(initial_value, final_value, actual_years)
        max_dd = max_drawdown(daily_values)
        sharpe = sharpe_ratio(daily_returns)
        vol = annualized_volatility(daily_returns)
        tot_ret = total_return(initial_value, final_value)
        w_rate = win_rate(all_trades)
        p_factor = profit_factor(all_trades)

        num_buys = sum(1 for t in all_trades if t["action"] == "BUY")
        num_sells = sum(1 for t in all_trades if t["action"] in ("SELL", "SELL_ALL"))
        total_trade_pnl = sum(t.get("pnl", 0) for t in all_trades)

        # Buy-and-hold metrics
        bh_total_return = (bh_final - initial_value) / initial_value if initial_value > 0 else 0

        results[pid] = {
            "persona": pid,
            "initial_value": round(initial_value, 2),
            "final_value": round(final_value, 2),
            "total_return_pct": round(tot_ret * 100, 2),
            "cagr_pct": round(cagr_val * 100, 2),
            "sharpe_ratio": round(sharpe, 3),
            "max_drawdown_pct": round(max_dd * 100, 2),
            "annualized_volatility_pct": round(vol * 100, 2),
            "num_trades": len(all_trades),
            "num_buys": num_buys,
            "num_sells": num_sells,
            "total_trade_pnl": round(total_trade_pnl, 2),
            "win_rate_pct": round(w_rate * 100, 1),
            "profit_factor": round(p_factor, 2) if p_factor != float("inf") else "∞",
            "buy_and_hold_return_pct": round(bh_total_return * 100, 2),
            "outperformance_pct": round((tot_ret - bh_total_return) * 100, 2),
            "final_cash": round(cash, 2),
            "final_holdings_count": len(holdings),
            "trading_days": n_days,
            "years": round(actual_years, 2),
        }

        # Print summary
        print(f"  [{pid.upper():8s}] Return: {tot_ret*100:+.1f}%  "
              f"CAGR: {cagr_val*100:+.1f}%  Sharpe: {sharpe:.2f}  "
              f"MaxDD: {max_dd*100:.1f}%  "
              f"vs B&H: {(tot_ret-bh_total_return)*100:+.1f}%  "
              f"({len(all_trades)} trades)")

    return results


def main():
    years = 2.0
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if arg.startswith("--years="):
                years = float(arg.split("=")[1])

    results = run_backtest(years)

    if not results:
        print("\n  No results — backtest failed")
        sys.exit(1)

    # Save results
    output_path = ROOT / "data" / "backtest_results.json"
    output = {
        "generated_at": datetime.now(MALAYSIA_TZ).isoformat(),
        "years": years,
        "personas": results,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2))
    print(f"\n  ✓ Results saved to {output_path}")

    # Summary comparison
    print(f"\n{'='*60}")
    print("Backtest Summary:")
    print(f"{'='*60}")
    for pid, r in sorted(results.items(), key=lambda x: x[1]["total_return_pct"], reverse=True):
        marker = "👑" if pid == max(results, key=lambda p: results[p]["total_return_pct"]) else "  "
        print(f"  {marker} {pid:8s}  {r['total_return_pct']:+.1f}%  "
              f"CAGR {r['cagr_pct']:+.1f}%  "
              f"Sharpe {r['sharpe_ratio']:.2f}  "
              f"MaxDD {r['max_drawdown_pct']:.1f}%  "
              f"vs B&H {r['outperformance_pct']:+.1f}%")


if __name__ == "__main__":
    main()
