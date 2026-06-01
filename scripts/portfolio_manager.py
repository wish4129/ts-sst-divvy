#!/usr/bin/env python3
"""Divvy Portfolio Manager — Hourly Bursa portfolio rebalancing engine.

Three personas (Ares, Demeter, Athena) each manage RM10,000 with distinct strategies.
Runs hourly Mon-Fri 9am-5pm. Uses yfinance for live KLSE prices.

Usage: python3 scripts/portfolio_manager.py [--dry-run]
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
MALAYSIA_TZ = timezone(timedelta(hours=8))

# ── Instrument lookup ──────────────────────────────────────────────

def load_stock_map(portfolios):
    """Build {ticker: {name, industry, initial_price}} from portfolios.json."""
    return portfolios["stocks"]


def fetch_prices(tickers):
    """Fetch current prices for Bursa tickers. Returns {ticker: price}."""
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

def ares_trade(persona, prices, snapshot, stock_map):
    """Ares: Cut -12%, ride winners, chase momentum. High turnover."""
    rules = persona["rules"]
    trades = []

    for name, s in snapshot["stocks"].items():
        pnl_pct = s["pnl_pct"] / 100

        # Hard stop loss
        if pnl_pct <= rules["stop_loss"]:
            trades.append({
                "action": "SELL_ALL", "stock": name,
                "reason": f"Stop loss triggered ({s['pnl_pct']:.1f}%)",
                "shares": s["shares"], "price": s["price"],
            })

    # If no stop-loss triggered, check for rebalance drift
    if not trades:
        for name, h in persona["holdings"].items():
            s = snapshot["stocks"].get(name)
            if not s:
                continue
            current_weight = s["weight"] / 100
            drift = abs(current_weight - h["target_pct"] / 100)
            if drift > rules["rebalance_drift"]:
                direction = "BUY" if current_weight < h["target_pct"] / 100 else "SELL"
                trades.append({
                    "action": direction, "stock": name,
                    "reason": f"Rebalance drift {drift*100:.1f}% (target {h['target_pct']}%)",
                    "shares": int(s["shares"] * drift * 0.5), "price": s["price"],
                })

    return trades


def demeter_trade(persona, prices, snapshot, stock_map):
    """Demeter: Hold forever. Only sell on dividend cut (external signal)."""
    trades = []
    # Demeter does NOT sell on price drops.
    # Only check: if cash > buffer, rebalance towards targets.
    rules = persona["rules"]
    cash_pct = snapshot["cash"] / snapshot["total"] if snapshot["total"] > 0 else 0

    if cash_pct > rules["cash_buffer"] + 0.05:
        # Excess cash — buy most underweight
        most_under = None
        max_under = 0
        for name, h in persona["holdings"].items():
            s = snapshot["stocks"].get(name)
            if not s:
                continue
            under = h["target_pct"] / 100 - s["weight"] / 100
            if under > max_under:
                max_under = under
                most_under = name
        if most_under and max_under > rules["rebalance_drift"]:
            excess = snapshot["total"] * (cash_pct - rules["cash_buffer"])
            shares = int(excess * 0.5 / snapshot["stocks"][most_under]["price"])
            if shares > 0:
                trades.append({
                    "action": "BUY", "stock": most_under,
                    "reason": f"Deploying excess cash ({cash_pct*100:.1f}% > {rules['cash_buffer']*100:.0f}%)",
                    "shares": shares, "price": snapshot["stocks"][most_under]["price"],
                })

    return trades


def athena_trade(persona, prices, snapshot, stock_map):
    """Athena: Sell 50% at +25%, buy 50% more at -10%. Tactical rotation."""
    rules = persona["rules"]
    trades = []

    for name, s in snapshot["stocks"].items():
        pnl_pct = s["pnl_pct"] / 100

        # Take profit: sell 50%
        if rules["take_profit"] and pnl_pct >= rules["take_profit"]:
            sell_shares = int(s["shares"] * rules["take_profit_sell_pct"])
            if sell_shares > 0:
                trades.append({
                    "action": "SELL", "stock": name,
                    "reason": f"Take profit +{s['pnl_pct']:.1f}% (sell {rules['take_profit_sell_pct']*100:.0f}%)",
                    "shares": sell_shares, "price": s["price"],
                })

        # Stop loss
        if rules["stop_loss"] and pnl_pct <= rules["stop_loss"]:
            trades.append({
                "action": "SELL_ALL", "stock": name,
                "reason": f"Stop loss ({s['pnl_pct']:.1f}%)",
                "shares": s["shares"], "price": s["price"],
            })

        # Dip buy: add 50% more
        if rules["dip_buy_threshold"] and pnl_pct <= rules["dip_buy_threshold"] and pnl_pct > (rules["stop_loss"] or -999):
            buy_shares = int(s["shares"] * rules["dip_buy_pct"])
            if buy_shares > 0:
                trades.append({
                    "action": "BUY", "stock": name,
                    "reason": f"Dip buy at {s['pnl_pct']:.1f}% (add {rules['dip_buy_pct']*100:.0f}%)",
                    "shares": buy_shares, "price": s["price"],
                })

    # Check rebalance drift for non-triggered stocks
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
                trades.append({
                    "action": direction, "stock": name,
                    "reason": f"Rebalance drift {drift*100:.1f}%",
                    "shares": adjust_shares, "price": s["price"],
                })

    return trades


TRADE_ENGINES = {"ares": ares_trade, "demeter": demeter_trade, "athena": athena_trade}


# ── Main ───────────────────────────────────────────────────────────

def main():
    dry_run = "--dry-run" in sys.argv
    now = datetime.now(MALAYSIA_TZ)
    timestamp = now.strftime("%Y-%m-%dT%H:%M:%S+08:00")

    # Load state
    portfolios = json.loads(PORTFOLIOS_PATH.read_text())
    stock_map = load_stock_map(portfolios)

    # Fetch live prices
    print(f"[{timestamp}] Fetching prices...")
    prices = fetch_prices(stock_map)
    print(f"  Prices: {json.dumps({k: round(v, 4) for k, v in prices.items()})}")

    # Load history
    history = {"runs": [], "personas": {}}
    if HISTORY_PATH.exists():
        history = json.loads(HISTORY_PATH.read_text())

    # Process each persona
    run_record = {"timestamp": timestamp, "personas": {}, "prices": prices}

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

        # Run trading engine
        engine = TRADE_ENGINES.get(pid)
        if engine:
            trades = engine(persona, prices, snapshot, stock_map)
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
                if cost <= state["cash"] * 1.05:  # Allow 5% margin
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
    # Keep last 500 runs
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
