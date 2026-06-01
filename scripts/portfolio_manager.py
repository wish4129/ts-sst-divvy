#!/usr/bin/env python3
"""Divvy Portfolio Manager — Hourly Bursa portfolio rebalancing engine.

Three personas (Ares, Demeter, Athena) each manage RM10,000 with distinct strategies.
Runs hourly Mon-Fri 9am-5pm. Uses yfinance for live KLSE prices.
Kronos 30-day AI forecasts integrated into all persona engines.

Usage: python3 scripts/portfolio_manager.py [--dry-run] [--skip-kronos]
"""

import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    import yfinance as yf
except ImportError:
    print("Installing yfinance...")
    os.system(f"{sys.executable} -m pip install yfinance --quiet")
    import yfinance as yf

ROOT = Path(__file__).resolve().parent.parent
PORTFOLIOS_PATH = ROOT / "scripts" / "portfolios.json"
HISTORY_PATH = ROOT / "data" / "portfolio_history.json"
LIVE_PRICES_PATH = ROOT / "data" / "live_prices.json"
KRONOS_PATH = ROOT / "data" / "kronos_forecast.json"
MALAYSIA_TZ = timezone(timedelta(hours=8))

# ── Kronos forecast integration ────────────────────────────────────

def load_kronos_forecasts():
    """Load 30-day Kronos price forecasts. Returns {stock: {pred_change_pct, pred_30d_close, ...}}."""
    if not KRONOS_PATH.exists():
        print("  [Kronos] No forecast file — running without AI signals")
        return {}
    try:
        data = json.loads(KRONOS_PATH.read_text())
        forecasts = {k: v for k, v in data.items() if "error" not in v}
        bulls = sum(1 for f in forecasts.values() if f.get("pred_change_pct", 0) > 0)
        bears = len(forecasts) - bulls
        print(f"  [Kronos] Loaded {len(forecasts)} forecasts ({bulls}▲ {bears}▼)")
        return forecasts
    except Exception as e:
        print(f"  [Kronos] Failed to load: {e}")
        return {}

def kronos_signal(forecasts, stock_name):
    """Extract Kronos signal for a stock.
    Returns: {direction: 'bullish'|'bearish'|'neutral', strength: 1-10, change_pct: float}
    """
    if not forecasts:
        return {"direction": "neutral", "strength": 0, "change_pct": 0}
    f = forecasts.get(stock_name, {})
    if not f:
        return {"direction": "neutral", "strength": 0, "change_pct": 0}
    pct = f.get("pred_change_pct", 0)
    if pct >= 5:
        direction, strength = "bullish", min(10, int(pct))
    elif pct >= 2:
        direction, strength = "bullish", 5
    elif pct <= -5:
        direction, strength = "bearish", min(10, int(abs(pct)))
    elif pct <= -2:
        direction, strength = "bearish", 5
    else:
        direction, strength = "neutral", 3
    return {"direction": direction, "strength": strength, "change_pct": pct}


# ── Instrument lookup ──────────────────────────────────────────────

def load_stock_map(portfolios):
    """Build {ticker: {name, industry, initial_price}} from portfolios.json."""
    return portfolios["stocks"]


def fetch_prices(tickers):
    """Fetch current prices. Priority: live_prices.json > yfinance > initial."""
    # 1. Try Scrapling-generated live prices
    if LIVE_PRICES_PATH.exists():
        try:
            live = json.loads(LIVE_PRICES_PATH.read_text())
            if live:
                print(f"  ✓ Loaded {len(live)} prices from live_prices.json")
                return {k: live.get(k, v["initial"]) for k, v in tickers.items()}
        except Exception:
            pass

    # 2. Fall back to yfinance
    ticker_list = [t["code"] for t in tickers.values()]
    prices = {}
    try:
        data = yf.download(ticker_list, period="1d", progress=False, auto_adjust=True)
        if data.empty:
            print("⚠ yfinance returned empty data, using initial prices")
            return {k: v["initial"] for k, v in tickers.items()}

        close = data["Close"]
        if len(ticker_list) == 1:
            price = float(close.iloc[-1]) if not close.empty else list(tickers.values())[0]["initial"]
            prices[list(tickers.keys())[0]] = price
        else:
            for name, info in tickers.items():
                code = info["code"]
                if code in close.columns and not close[code].empty:
                    val = float(close[code].iloc[-1])
                    prices[name] = val if val > 0 else info["initial"]
                else:
                    prices[name] = info["initial"]
    except Exception as e:
        print(f"⚠ yfinance error: {e}, using initial prices")
        return {k: v["initial"] for k, v in tickers.items()}
    return prices


# ── Portfolio math ─────────────────────────────────────────────────

def calc_portfolio_value(holdings, prices, cash):
    """Calculate total value, invested value, and per-stock P&L."""
    total_invested = sum(h["shares"] * h["cost"] for h in holdings.values())
    total_current = sum(h["shares"] * prices.get(name, h["cost"]) for name, h in holdings.items())
    total = total_current + cash
    pnl = total - 10000  # initial capital RM10k
    pnl_pct = (pnl / 10000) * 100

    stocks_pnl = {}
    for name, h in holdings.items():
        current_price = prices.get(name, h["cost"])
        invested = h["shares"] * h["cost"]
        current = h["shares"] * current_price
        stocks_pnl[name] = {
            "shares": h["shares"],
            "cost": h["cost"],
            "price": round(current_price, 4),
            "invested": round(invested, 2),
            "current": round(current, 2),
            "pnl": round(current - invested, 2),
            "pnl_pct": round(((current_price - h["cost"]) / h["cost"]) * 100, 2),
            "weight": round((current / total * 100), 1) if total > 0 else 0,
        }
    return {
        "total": round(total, 2),
        "invested": round(total_invested, 2),
        "cash": round(cash, 2),
        "pnl": round(pnl, 2),
        "pnl_pct": round(pnl_pct, 2),
        "stocks": stocks_pnl,
    }


# ── Trading engines ────────────────────────────────────────────────

def ares_trade(persona, prices, snapshot, stock_map, prev_prices=None, forecasts=None):
    """Ares: Cut -12%, momentum cool -5%, ride winners.
    Kronos: overweight bullish (reduce trim, buy more), proactive trim on bearish.
    """
    rules = persona["rules"]
    trades = []

    for name, s in snapshot["stocks"].items():
        pnl_pct = s["pnl_pct"] / 100
        ksig = kronos_signal(forecasts, name)

        # Momentum cooling: trim 25% if dropped 5%+ from last run
        # BUT if Kronos says bullish (>5% forecast), only trim 7.5% — stay in the trade
        if prev_prices and name in prev_prices:
            prev_price = prev_prices[name]
            if prev_price > 0:
                session_change = (s["price"] - prev_price) / prev_price
                if session_change <= rules.get("momentum_cooling_threshold", -0.05):
                    trim_pct = rules.get("momentum_cooling_trim", 0.25)
                    if ksig["direction"] == "bullish" and ksig["change_pct"] >= 5:
                        trim_pct = trim_pct * 0.3
                        reason = f"Momentum cool {session_change*100:.1f}% (reduced trim — Kronos +{ksig['change_pct']:.1f}% forecast)"
                    else:
                        reason = f"Momentum cool {session_change*100:.1f}% (trim {rules['momentum_cooling_trim']*100:.0f}%)"
                    trim_shares = int(s["shares"] * trim_pct)
                    if trim_shares > 0:
                        trades.append({"action": "SELL", "stock": name, "reason": reason, "shares": trim_shares, "price": s["price"]})

        # Kronos proactive: if strongly bearish (<= -5%), trim 15% regardless
        if ksig["direction"] == "bearish" and ksig["strength"] >= 7:
            trim_shares = int(s["shares"] * 0.15)
            if trim_shares > 0:
                trades.append({"action": "SELL", "stock": name, "reason": f"Kronos bearish {ksig['change_pct']:+.1f}% — proactive trim 15%", "shares": trim_shares, "price": s["price"]})

        # Hard stop loss
        if pnl_pct <= rules["stop_loss"]:
            trades.append({"action": "SELL_ALL", "stock": name, "reason": f"Stop loss ({s['pnl_pct']:.1f}%)", "shares": s["shares"], "price": s["price"]})

    # Rebalance with Kronos bias: buy MORE if bullish+underweight, sell MORE if bearish+overweight
    triggered = {t["stock"] for t in trades if t["action"] == "SELL_ALL"}
    for name, h in persona["holdings"].items():
        if name in triggered:
            continue
        s = snapshot["stocks"].get(name)
        if not s:
            continue
        current_weight = s["weight"] / 100
        drift = abs(current_weight - h["target_pct"] / 100)
        if drift > rules["rebalance_drift"]:
            ksig = kronos_signal(forecasts, name)
            multiplier = 1.0
            ksig_note = ""
            if ksig["direction"] == "bullish" and current_weight < h["target_pct"] / 100:
                multiplier = 1.5
                ksig_note = f", Kronos ▲"
            elif ksig["direction"] == "bearish" and current_weight > h["target_pct"] / 100:
                multiplier = 1.5
                ksig_note = f", Kronos ▼"
            direction = "BUY" if current_weight < h["target_pct"] / 100 else "SELL"
            trades.append({"action": direction, "stock": name, "reason": f"Rebalance drift {drift*100:.1f}% (target {h['target_pct']}%{ksig_note})", "shares": int(s["shares"] * drift * 0.5 * multiplier), "price": s["price"]})

    return trades


def demeter_trade(persona, prices, snapshot, stock_map, prev_prices=None, forecasts=None):
    """Demeter: Hold forever. Sell only on dividend cut or DY<3%.
    Kronos: skip buying stocks with bearish forecasts even if underweight (safety first).
    Flag bearish stocks for dividend risk review.
    """
    trades = []
    rules = persona["rules"]
    cash_pct = snapshot["cash"] / snapshot["total"] if snapshot["total"] > 0 else 0
    min_dy = rules.get("min_dividend_yield", 0.03)

    if cash_pct > rules["cash_buffer"] + 0.05:
        # Deploy excess cash — but prefer bullish stocks, skip bearish ones
        best_name, best_score = None, -999
        for name, h in persona["holdings"].items():
            s = snapshot["stocks"].get(name)
            if not s:
                continue
            under = h["target_pct"] / 100 - s["weight"] / 100
            if under <= 0:
                continue
            ksig = kronos_signal(forecasts, name)
            # Safety: skip if Kronos predicts >5% drawdown
            if ksig["change_pct"] <= -5:
                print(f"  [Demeter] Skipping {name}: Kronos predicts {ksig['change_pct']:+.1f}% — dividend risk")
                continue
            # Score: underweight * (1 + Kronos bonus)
            score = under * (1 + max(0, ksig["change_pct"]) / 100)
            if score > best_score:
                best_score = score
                best_name = name

        if best_name and best_score > rules["rebalance_drift"]:
            excess = snapshot["total"] * (cash_pct - rules["cash_buffer"])
            s = snapshot["stocks"][best_name]
            shares = int(excess * 0.5 / s["price"])
            if shares > 0:
                ksig = kronos_signal(forecasts, best_name)
                kronos_note = f" (Kronos {ksig['change_pct']:+.1f}%)" if forecasts else ""
                trades.append({"action": "BUY", "stock": best_name, "reason": f"Deploy excess cash ({cash_pct*100:.1f}% > {rules['cash_buffer']*100:.0f}%) → {best_name}{kronos_note}", "shares": shares, "price": s["price"]})

    # DY < 3% trim: sell 50% if price run-up compressed yield too far
    for name, s in snapshot["stocks"].items():
        stock_info = stock_map.get(name, {})
        initial_price = stock_info.get("initial", s["cost"])
        if s["price"] >= initial_price * 1.67:
            trim_shares = int(s["shares"] * 0.5)
            if trim_shares > 0:
                trades.append({"action": "SELL", "stock": name, "reason": f"DY compression: price +{(s['price']/initial_price-1)*100:.0f}% from initial (DY likely <{min_dy*100:.0f}%)", "shares": trim_shares, "price": s["price"]})

    return trades


def athena_trade(persona, prices, snapshot, stock_map, prev_prices=None, forecasts=None):
    """Athena: Sell 50% @ +25%, full exit @ +40%, dip buy @ -10% (1/month).
    Kronos: confirm dip buys (only buy if forecast says recovery, not further decline).
    """
    rules = persona["rules"]
    trades = []

    for name, s in snapshot["stocks"].items():
        pnl_pct = s["pnl_pct"] / 100

        # Full exit at extreme profit
        full_exit = rules.get("full_exit_threshold", 0.40)
        if full_exit and pnl_pct >= full_exit:
            trades.append({"action": "SELL_ALL", "stock": name, "reason": f"Full exit +{s['pnl_pct']:.1f}% (threshold {full_exit*100:.0f}%)", "shares": s["shares"], "price": s["price"]})
            continue

        # Take profit: sell 50%
        if rules["take_profit"] and pnl_pct >= rules["take_profit"]:
            sell_shares = int(s["shares"] * rules["take_profit_sell_pct"])
            if sell_shares > 0:
                trades.append({"action": "SELL", "stock": name, "reason": f"Take profit +{s['pnl_pct']:.1f}% (sell {rules['take_profit_sell_pct']*100:.0f}%)", "shares": sell_shares, "price": s["price"]})

        # Stop loss
        if rules["stop_loss"] and pnl_pct <= rules["stop_loss"]:
            trades.append({"action": "SELL_ALL", "stock": name, "reason": f"Stop loss ({s['pnl_pct']:.1f}%)", "shares": s["shares"], "price": s["price"]})
            continue

        # Dip buy: add 50% more — BUT only if Kronos confirms recovery
        can_dip_buy = True
        if prev_prices and name in prev_prices:
            h = persona["holdings"].get(name)
            if h and s["shares"] > h["shares"] * 1.4:
                can_dip_buy = False

        if can_dip_buy and rules.get("dip_buy_threshold") and pnl_pct <= rules["dip_buy_threshold"] and pnl_pct > (rules["stop_loss"] or -999):
            # Kronos check: only dip buy if forecast is neutral or better (> -5%)
            ksig = kronos_signal(forecasts, name)
            if ksig["change_pct"] < -5:
                print(f"  [Athena] Skipping dip buy {name}: Kronos predicts {ksig['change_pct']:+.1f}% — waiting for clearer bottom")
                continue
            buy_shares = int(s["shares"] * rules["dip_buy_pct"])
            if buy_shares > 0:
                kronos_note = f" (Kronos {ksig['change_pct']:+.1f}% — recovery signal)" if forecasts and ksig["change_pct"] > 0 else ""
                trades.append({"action": "BUY", "stock": name, "reason": f"Dip buy at {s['pnl_pct']:.1f}%{kronos_note}", "shares": buy_shares, "price": s["price"]})

    # Rebalance drift for non-triggered stocks
    triggered = {t["stock"] for t in trades if t["action"].startswith("SELL")}
    for name, h in persona["holdings"].items():
        if name in triggered:
            continue
        s = snapshot["stocks"].get(name)
        if not s:
            continue
        current_weight = s["weight"] / 100
        drift = abs(current_weight - h["target_pct"] / 100)
        if drift > rules["rebalance_drift"]:
            direction = "BUY" if current_weight < h["target_pct"] / 100 else "SELL"
            adjust_shares = int(s["shares"] * drift * 0.3)
            if adjust_shares > 0:
                trades.append({"action": direction, "stock": name, "reason": f"Rebalance drift {drift*100:.1f}%", "shares": adjust_shares, "price": s["price"]})

    return trades


TRADE_ENGINES = {"ares": ares_trade, "demeter": demeter_trade, "athena": athena_trade}


# ── Main ───────────────────────────────────────────────────────────

def main():
    dry_run = "--dry-run" in sys.argv
    skip_kronos = "--skip-kronos" in sys.argv
    now = datetime.now(MALAYSIA_TZ)
    timestamp = now.strftime("%Y-%m-%dT%H:%M:%S+08:00")

    # Load state
    portfolios = json.loads(PORTFOLIOS_PATH.read_text())
    stock_map = load_stock_map(portfolios)

    # Load Kronos forecasts (unless skipped)
    forecasts = {} if skip_kronos else load_kronos_forecasts()

    # Fetch live prices
    print(f"[{timestamp}] Fetching prices...")
    prices = fetch_prices(stock_map)
    print(f"  Prices: {json.dumps({k: round(v, 4) for k, v in prices.items()})}")

    # Load history
    history = {"runs": [], "personas": {}}
    if HISTORY_PATH.exists():
        history = json.loads(HISTORY_PATH.read_text())

    # Process each persona
    run_record = {
        "timestamp": timestamp,
        "personas": {},
        "prices": prices,
        "kronos": bool(forecasts),
    }

    # Get previous prices for momentum comparison
    prev_prices = {}
    if history.get("runs"):
        prev_run = history["runs"][-1]
        prev_prices = prev_run.get("prices", {})

    for pid, persona in portfolios["personas"].items():
        # Load running state
        state = history.get("personas", {}).get(pid, {
            "cash": 10000 - sum(h["shares"] * h["cost"] for h in persona["holdings"].values()),
            "holdings": {name: {"shares": h["shares"], "cost": h["cost"]}
                        for name, h in persona["holdings"].items()},
            "trade_log": [],
        })

        # Calculate current value
        snapshot = calc_portfolio_value(state["holdings"], prices, state["cash"])

        # Run trading engine (pass forecasts)
        engine = TRADE_ENGINES.get(pid)
        if engine:
            trades = engine(persona, prices, snapshot, stock_map, prev_prices, forecasts)
        else:
            trades = []

        # Execute trades
        executed = []
        for t in trades:
            if t["action"] == "SELL_ALL":
                sell_shares = state["holdings"][t["stock"]]["shares"]
                proceeds = sell_shares * t["price"]
                state["cash"] += proceeds
                del state["holdings"][t["stock"]]
                executed.append({**t, "proceeds": round(proceeds, 2)})
            elif t["action"] == "SELL":
                sell_shares = min(t["shares"], state["holdings"][t["stock"]]["shares"])
                proceeds = sell_shares * t["price"]
                state["cash"] += proceeds
                state["holdings"][t["stock"]]["shares"] -= sell_shares
                if state["holdings"][t["stock"]]["shares"] <= 0:
                    del state["holdings"][t["stock"]]
                executed.append({**t, "proceeds": round(proceeds, 2), "shares": sell_shares})
            elif t["action"] == "BUY":
                cost = t["shares"] * t["price"]
                if cost <= state["cash"] * 1.05:
                    actual_shares = min(t["shares"], int(state["cash"] / t["price"]))
                    if actual_shares > 0:
                        actual_cost = actual_shares * t["price"]
                        state["cash"] -= actual_cost
                        if t["stock"] in state["holdings"]:
                            old = state["holdings"][t["stock"]]
                            total_shares = old["shares"] + actual_shares
                            old["cost"] = ((old["cost"] * old["shares"]) + actual_cost) / total_shares
                            old["shares"] = total_shares
                        else:
                            state["holdings"][t["stock"]] = {"shares": actual_shares, "cost": t["price"]}
                        executed.append({**t, "cost": round(actual_cost, 2), "shares": actual_shares})

        if dry_run:
            for t in trades:
                print(f"  [{pid}] WOULD {t['action']} {t['stock']}: {t['reason']}")
        else:
            for e in executed:
                print(f"  [{pid}] {e['action']} {e['stock']} x{e.get('shares', 'ALL')} @ {e['price']}: {e['reason']}")
                state["trade_log"].append({**e, "timestamp": timestamp})

        # Recalculate after trades
        final_snapshot = calc_portfolio_value(state["holdings"], prices, state["cash"])

        # Save state
        history["personas"][pid] = state

        summary = {
            "total": final_snapshot["total"],
            "invested": final_snapshot["invested"],
            "cash": final_snapshot["cash"],
            "pnl": final_snapshot["pnl"],
            "pnl_pct": final_snapshot["pnl_pct"],
            "holdings": final_snapshot["stocks"],
            "trades_this_run": len(executed),
        }
        run_record["personas"][pid] = summary

        print(f"  [{pid}] Total: RM{final_snapshot['total']:.2f} | P&L: {final_snapshot['pnl_pct']:+.2f}% | Trades: {len(executed)}")

    # Append run
    history["runs"].append(run_record)
    if len(history["runs"]) > 500:
        history["runs"] = history["runs"][-500:]

    if not dry_run:
        HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        HISTORY_PATH.write_text(json.dumps(history, indent=2))
        print(f"  ✓ Saved {len(run_record['personas'])} persona snapshots to history")

    # Print leaderboard
    print("\n═══ LEADERBOARD ═══")
    ranked = sorted(run_record["personas"].items(), key=lambda x: x[1]["pnl_pct"], reverse=True)
    medals = ["🥇", "🥈", "🥉"]
    for i, (pid, s) in enumerate(ranked):
        print(f"  {medals[i]} {pid.upper()}: RM{s['total']:.2f} ({s['pnl_pct']:+.2f}%) — {portfolios['personas'][pid]['god']}")

    return run_record


if __name__ == "__main__":
    main()
