#!/usr/bin/env python3
"""Divvy Portfolio Manager — SQLite-backed Bursa portfolio rebalancing engine.

Three personas (Ares, Demeter, Athena) each manage configurable capital.
All trades recorded with full decision trail (reason, Kronos signal, source).
Runs hourly. Kronos 30-day AI forecasts integrated into all engines.

Schema: schema.sql (SQLite local → Supabase Postgres future, near-identical)

Usage: python3 scripts/portfolio_manager.py [--dry-run] [--skip-kronos] [--export-json]
"""

import json
import os
import sqlite3
import sys
import time
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    import yfinance as yf
except ImportError:
    print("Installing yfinance...")
    os.system(f"{sys.executable} -m pip install yfinance --quiet")
    import yfinance as yf

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "divvy.db"
PORTFOLIOS_PATH = ROOT / "scripts" / "portfolios.json"
HISTORY_PATH = ROOT / "data" / "portfolio_history.json"
LIVE_PRICES_PATH = ROOT / "data" / "live_prices.json"
KRONOS_PATH = ROOT / "data" / "kronos_forecast.json"
MALAYSIA_TZ = timezone(timedelta(hours=8))


# ── DB helpers ─────────────────────────────────────────────────────

def get_db():
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")
    return db


def load_portfolios_from_db(db):
    """Load all 3 persona portfolios with holdings from SQLite."""
    portfolios = {}
    for row in db.execute("SELECT * FROM user_portfolios WHERE user_id='kevin' ORDER BY persona"):
        pid = row['persona']
        holdings = {}
        for h in db.execute(
            "SELECT ph.*, s.name as stock_name FROM portfolio_holdings ph JOIN stocks s ON ph.stock_id=s.id WHERE portfolio_id=?",
            (row['id'],)
        ):
            holdings[h['stock_name']] = {
                'shares': h['shares'], 'cost': h['avg_cost'], 'target_pct': h['target_pct']
            }
        portfolios[pid] = {
            'id': row['id'],
            'name': row['name'],
            'god': _persona_god(pid),
            'style': _persona_style(pid),
            'strategy': row['strategy'],
            'initial_capital': row['initial_capital'],
            'cash': row['cash'],
            'holdings': holdings,
            'rules': _persona_rules(pid),
        }
    return portfolios


def load_stock_map(db):
    """Build {short_name: {code, name, industry, initial}} from DB + portfolios.json fallback.
    Uses short names (MAYBANK) as keys matching live_prices.json and portfolios.json."""
    # Read portfolios.json for short name → code mapping
    try:
        pf = json.loads(PORTFOLIOS_PATH.read_text())
        pf_stocks = pf.get("stocks", {})
    except Exception:
        pf_stocks = {}

    stock_map = {}
    for row in db.execute("SELECT * FROM stocks WHERE status != 'removed'"):
        # Find short name from portfolios.json (or use full name as fallback)
        short_name = row['name']  # default
        for sn, info in pf_stocks.items():
            if info.get('code') == row['id']:
                short_name = sn
                break
        stock_map[short_name] = {
            'code': row['id'],
            'name': row['name'],
            'industry': row['industry'] or '',
            'initial': row['initial_price'],
        }
    return stock_map


def save_trade(db, portfolio_id, stock_id, action, shares, price, reason, kronos_signal, decision_source, triggered_by, snapshot_id, timestamp):
    """Record trade with full decision trail."""
    db.execute("""INSERT INTO trades (portfolio_id, stock_id, action, shares, price, total_amount,
                   reason, kronos_signal, decision_source, triggered_by, snapshot_id, executed_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
               (portfolio_id, stock_id, action, shares, price, shares * price,
                reason, json.dumps(kronos_signal) if kronos_signal else None,
                decision_source, triggered_by, snapshot_id, timestamp))
    return db.execute("SELECT last_insert_rowid()").fetchone()[0]


def save_snapshot(db, portfolio_id, timestamp, total, invested, cash, pnl, pnl_pct, holdings):
    """Save portfolio performance snapshot."""
    db.execute("""INSERT INTO portfolio_snapshots (portfolio_id, snapshot_at, total_value, invested, cash, pnl, pnl_pct, holdings_json)
                  VALUES (?,?,?,?,?,?,?,?)""",
               (portfolio_id, timestamp, total, invested, cash, pnl, pnl_pct, json.dumps(holdings)))
    return db.execute("SELECT last_insert_rowid()").fetchone()[0]


def update_portfolio_cash(db, portfolio_id, cash):
    db.execute("UPDATE user_portfolios SET cash=?, updated_at=? WHERE id=?", (cash, datetime.now(MALAYSIA_TZ).isoformat(), portfolio_id))


def update_holding(db, portfolio_id, stock_id, shares, avg_cost, target_pct):
    if shares <= 0:
        db.execute("DELETE FROM portfolio_holdings WHERE portfolio_id=? AND stock_id=?", (portfolio_id, stock_id))
    else:
        db.execute("""INSERT INTO portfolio_holdings (portfolio_id, stock_id, shares, avg_cost, target_pct)
                      VALUES (?,?,?,?,?) ON CONFLICT(portfolio_id, stock_id) DO UPDATE SET shares=excluded.shares, avg_cost=excluded.avg_cost, target_pct=excluded.target_pct""",
                   (portfolio_id, stock_id, shares, avg_cost, target_pct))


def export_json_for_web(db, personas_data):
    """Export portfolio_history.json for the static web app (backward compat)."""
    history = {"runs": [], "personas": {}}
    if HISTORY_PATH.exists():
        try:
            history = json.loads(HISTORY_PATH.read_text())
        except Exception:
            pass

    # Append snapshots as runs
    snapshots = db.execute("""SELECT * FROM portfolio_snapshots ORDER BY snapshot_at DESC LIMIT 50""").fetchall()
    for s in snapshots:
        run = {
            "timestamp": s['snapshot_at'],
            "personas": {},
        }
        # Group by portfolio
        pid_map = {}
        for pf in db.execute("SELECT * FROM user_portfolios WHERE user_id='kevin'"):
            pid_map[pf['id']] = pf['persona']

        snap_pid = pid_map.get(s['portfolio_id'], 'unknown')
        run["personas"][snap_pid] = {
            "total": s['total_value'],
            "invested": s['invested'],
            "cash": s['cash'],
            "pnl": s['pnl'],
            "pnl_pct": s['pnl_pct'],
            "holdings": json.loads(s['holdings_json']) if s['holdings_json'] else {},
            "trades_this_run": 0,
        }
        history["runs"].append(run)

    # Also save persona state
    for pid, pdata in personas_data.items():
        history["personas"][pid] = {
            "cash": pdata['cash'],
            "holdings": {name: {"shares": h['shares'], "cost": h['cost']} for name, h in pdata['holdings'].items()},
            "trade_log": [],
        }

    if len(history["runs"]) > 500:
        history["runs"] = history["runs"][-500:]

    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_PATH.write_text(json.dumps(history, indent=2))
    print(f"  ✓ Exported {len(history['runs'])} snapshots to portfolio_history.json")


# ── Persona metadata (hardcoded — in portfolios.json for now, DB later) ──

def _persona_god(pid):
    return {"ares": "God of War", "demeter": "Harvest Goddess", "athena": "Goddess of Wisdom"}.get(pid, pid)

def _persona_style(pid):
    return {"ares": "Aggressive", "demeter": "Conservative", "athena": "Hybrid"}.get(pid, pid)

def _persona_rules(pid):
    rules = {
        "ares": {"stop_loss": -0.12, "take_profit": None, "max_single_position": 0.25, "min_stocks": 4,
                 "rebalance_drift": 0.07, "cash_buffer": 0.0, "dividend_reinvest": True,
                 "momentum_cooling_threshold": -0.05, "momentum_cooling_trim": 0.25},
        "demeter": {"stop_loss": None, "take_profit": None, "max_single_position": 0.35, "min_stocks": 4,
                    "rebalance_drift": 0.10, "cash_buffer": 0.10, "dividend_reinvest": True,
                    "fd_rate": 0.03, "min_dividend_yield": 0.03},
        "athena": {"stop_loss": -0.10, "take_profit": 0.25, "take_profit_sell_pct": 0.50,
                   "max_single_position": 0.30, "min_stocks": 5, "rebalance_drift": 0.10,
                   "dip_buy_threshold": -0.10, "dip_buy_pct": 0.50, "cash_buffer": 0.0,
                   "dividend_reinvest": True, "full_exit_threshold": 0.40, "dip_buy_cooldown_days": 30},
    }
    return rules.get(pid, {})


# ── Kronos forecast integration ────────────────────────────────────

def load_kronos_forecasts():
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
        print(f"  [Kronos] Failed: {e}")
        return {}

def kronos_signal(forecasts, stock_name):
    if not forecasts:
        return {"direction": "neutral", "strength": 0, "change_pct": 0}
    f = forecasts.get(stock_name, {})
    if not f:
        return {"direction": "neutral", "strength": 0, "change_pct": 0}
    pct = f.get("pred_change_pct", 0)
    if pct >= 5:       direction, strength = "bullish", min(10, int(pct))
    elif pct >= 2:     direction, strength = "bullish", 5
    elif pct <= -5:    direction, strength = "bearish", min(10, int(abs(pct)))
    elif pct <= -2:    direction, strength = "bearish", 5
    else:              direction, strength = "neutral", 3
    return {"direction": direction, "strength": strength, "change_pct": pct}


# ── Instrument lookup ──────────────────────────────────────────────

def fetch_prices(tickers):
    if LIVE_PRICES_PATH.exists():
        try:
            live = json.loads(LIVE_PRICES_PATH.read_text())
            if live:
                print(f"  ✓ Loaded {len(live)} prices from live_prices.json")
                return {k: live.get(k, v["initial"]) for k, v in tickers.items()}
        except Exception:
            pass

    ticker_list = [t["code"] for t in tickers.values()]
    prices = {}
    try:
        data = yf.download(ticker_list, period="1d", progress=False, auto_adjust=True)
        if data.empty:
            print("⚠ yfinance empty, using initial prices")
            return {k: v["initial"] for k, v in tickers.items()}
        close = data["Close"]
        for name, info in tickers.items():
            code = info["code"]
            if len(ticker_list) == 1:
                prices[name] = float(close.iloc[-1]) if not close.empty else info["initial"]
            elif code in close.columns and not close[code].empty:
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
    total_invested = sum(h["shares"] * h["cost"] for h in holdings.values())
    total_current = sum(h["shares"] * prices.get(name, h["cost"]) for name, h in holdings.items())
    total = total_current + cash
    pnl = total - 10000
    pnl_pct = (pnl / 10000) * 100

    stocks_pnl = {}
    for name, h in holdings.items():
        current_price = prices.get(name, h["cost"])
        invested = h["shares"] * h["cost"]
        current = h["shares"] * current_price
        stocks_pnl[name] = {
            "shares": h["shares"], "cost": h["cost"], "price": round(current_price, 4),
            "invested": round(invested, 2), "current": round(current, 2),
            "pnl": round(current - invested, 2),
            "pnl_pct": round(((current_price - h["cost"]) / h["cost"]) * 100, 2),
            "weight": round((current / total * 100), 1) if total > 0 else 0,
        }
    return {"total": round(total, 2), "invested": round(total_invested, 2),
            "cash": round(cash, 2), "pnl": round(pnl, 2), "pnl_pct": round(pnl_pct, 2),
            "stocks": stocks_pnl}


# ── Trading engines ────────────────────────────────────────────────

def ares_trade(persona, prices, snapshot, stock_map, prev_prices=None, forecasts=None):
    rules = persona["rules"]
    trades = []
    for name, s in snapshot["stocks"].items():
        pnl_pct = s["pnl_pct"] / 100
        ksig = kronos_signal(forecasts, name)

        if prev_prices and name in prev_prices:
            prev_price = prev_prices[name]
            if prev_price > 0:
                session_change = (s["price"] - prev_price) / prev_price
                if session_change <= rules.get("momentum_cooling_threshold", -0.05):
                    trim_pct = rules.get("momentum_cooling_trim", 0.25)
                    if ksig["direction"] == "bullish" and ksig["change_pct"] >= 5:
                        trim_pct *= 0.3
                        reason = f"Momentum cool {session_change*100:.1f}% (reduced trim — Kronos +{ksig['change_pct']:.1f}%)"
                    else:
                        reason = f"Momentum cool {session_change*100:.1f}% (trim {rules['momentum_cooling_trim']*100:.0f}%)"
                    trim_shares = int(s["shares"] * trim_pct)
                    if trim_shares > 0:
                        trades.append({"action": "SELL", "stock": name, "reason": reason, "shares": trim_shares, "price": s["price"],
                                       "source": "momentum_cooling", "signal": ksig})

        if ksig["direction"] == "bearish" and ksig["strength"] >= 7:
            trim_shares = int(s["shares"] * 0.15)
            if trim_shares > 0:
                trades.append({"action": "SELL", "stock": name,
                               "reason": f"Kronos bearish {ksig['change_pct']:+.1f}% — proactive trim 15%",
                               "shares": trim_shares, "price": s["price"],
                               "source": "kronos_bearish_trim", "signal": ksig})

        if pnl_pct <= rules["stop_loss"]:
            trades.append({"action": "SELL_ALL", "stock": name, "reason": f"Stop loss ({s['pnl_pct']:.1f}%)",
                           "shares": s["shares"], "price": s["price"], "source": "stop_loss", "signal": ksig})

    triggered = {t["stock"] for t in trades if t["action"] == "SELL_ALL"}
    for name, h in persona["holdings"].items():
        if name in triggered: continue
        s = snapshot["stocks"].get(name)
        if not s: continue
        current_weight = s["weight"] / 100
        drift = abs(current_weight - h["target_pct"] / 100)
        if drift > rules["rebalance_drift"]:
            ksig = kronos_signal(forecasts, name)
            multiplier = 1.0
            ksig_note = ""
            if ksig["direction"] == "bullish" and current_weight < h["target_pct"] / 100:
                multiplier = 1.5; ksig_note = ", Kronos ▲"
            elif ksig["direction"] == "bearish" and current_weight > h["target_pct"] / 100:
                multiplier = 1.5; ksig_note = ", Kronos ▼"
            direction = "BUY" if current_weight < h["target_pct"] / 100 else "SELL"
            trades.append({"action": direction, "stock": name,
                           "reason": f"Rebalance drift {drift*100:.1f}% (target {h['target_pct']}%{ksig_note})",
                           "shares": int(s["shares"] * drift * 0.5 * multiplier), "price": s["price"],
                           "source": "rebalance", "signal": ksig})
    return trades


def demeter_trade(persona, prices, snapshot, stock_map, prev_prices=None, forecasts=None):
    trades = []
    rules = persona["rules"]
    cash_pct = snapshot["cash"] / snapshot["total"] if snapshot["total"] > 0 else 0
    min_dy = rules.get("min_dividend_yield", 0.03)

    if cash_pct > rules["cash_buffer"] + 0.05:
        best_name, best_score = None, -999
        for name, h in persona["holdings"].items():
            s = snapshot["stocks"].get(name)
            if not s: continue
            under = h["target_pct"] / 100 - s["weight"] / 100
            if under <= 0: continue
            ksig = kronos_signal(forecasts, name)
            if ksig["change_pct"] <= -5:
                print(f"  [Demeter] Skipping {name}: Kronos {ksig['change_pct']:+.1f}% — dividend risk")
                continue
            score = under * (1 + max(0, ksig["change_pct"]) / 100)
            if score > best_score:
                best_score = score; best_name = name

        if best_name and best_score > rules["rebalance_drift"]:
            excess = snapshot["total"] * (cash_pct - rules["cash_buffer"])
            s = snapshot["stocks"][best_name]
            shares = int(excess * 0.5 / s["price"])
            if shares > 0:
                ksig = kronos_signal(forecasts, best_name)
                kronos_note = f" (Kronos {ksig['change_pct']:+.1f}%)" if forecasts else ""
                trades.append({"action": "BUY", "stock": best_name,
                               "reason": f"Deploy excess cash ({cash_pct*100:.1f}% > {rules['cash_buffer']*100:.0f}%) → {best_name}{kronos_note}",
                               "shares": shares, "price": s["price"], "source": "excess_cash_deployment", "signal": ksig})

    for name, s in snapshot["stocks"].items():
        stock_info = stock_map.get(name, {})
        initial_price = stock_info.get("initial", s["cost"])
        if s["price"] >= initial_price * 1.67:
            trim_shares = int(s["shares"] * 0.5)
            if trim_shares > 0:
                trades.append({"action": "SELL", "stock": name,
                               "reason": f"DY compression: price +{(s['price']/initial_price-1)*100:.0f}% (DY likely <{min_dy*100:.0f}%)",
                               "shares": trim_shares, "price": s["price"], "source": "dy_compression", "signal": {}})
    return trades


def athena_trade(persona, prices, snapshot, stock_map, prev_prices=None, forecasts=None):
    rules = persona["rules"]
    trades = []
    for name, s in snapshot["stocks"].items():
        pnl_pct = s["pnl_pct"] / 100

        full_exit = rules.get("full_exit_threshold", 0.40)
        if full_exit and pnl_pct >= full_exit:
            trades.append({"action": "SELL_ALL", "stock": name, "reason": f"Full exit +{s['pnl_pct']:.1f}% (≥{full_exit*100:.0f}%)",
                           "shares": s["shares"], "price": s["price"], "source": "full_exit", "signal": {}})
            continue

        if rules["take_profit"] and pnl_pct >= rules["take_profit"]:
            sell_shares = int(s["shares"] * rules["take_profit_sell_pct"])
            if sell_shares > 0:
                trades.append({"action": "SELL", "stock": name, "reason": f"Take profit +{s['pnl_pct']:.1f}% (sell {rules['take_profit_sell_pct']*100:.0f}%)",
                               "shares": sell_shares, "price": s["price"], "source": "take_profit", "signal": {}})

        if rules["stop_loss"] and pnl_pct <= rules["stop_loss"]:
            trades.append({"action": "SELL_ALL", "stock": name, "reason": f"Stop loss ({s['pnl_pct']:.1f}%)",
                           "shares": s["shares"], "price": s["price"], "source": "stop_loss", "signal": {}})
            continue

        can_dip_buy = True
        if prev_prices and name in prev_prices:
            h = persona["holdings"].get(name)
            if h and s["shares"] > h["shares"] * 1.4:
                can_dip_buy = False

        if can_dip_buy and rules.get("dip_buy_threshold") and pnl_pct <= rules["dip_buy_threshold"] and pnl_pct > (rules["stop_loss"] or -999):
            ksig = kronos_signal(forecasts, name)
            if ksig["change_pct"] < -5:
                print(f"  [Athena] Skipping dip buy {name}: Kronos {ksig['change_pct']:+.1f}% — waiting for clearer bottom")
                continue
            buy_shares = int(s["shares"] * rules["dip_buy_pct"])
            if buy_shares > 0:
                kronos_note = f" (Kronos {ksig['change_pct']:+.1f}% — recovery signal)" if forecasts and ksig["change_pct"] > 0 else ""
                trades.append({"action": "BUY", "stock": name, "reason": f"Dip buy at {s['pnl_pct']:.1f}%{kronos_note}",
                               "shares": buy_shares, "price": s["price"], "source": "dip_buy", "signal": ksig})

    triggered = {t["stock"] for t in trades if t["action"].startswith("SELL")}
    for name, h in persona["holdings"].items():
        if name in triggered: continue
        s = snapshot["stocks"].get(name)
        if not s: continue
        current_weight = s["weight"] / 100
        drift = abs(current_weight - h["target_pct"] / 100)
        if drift > rules["rebalance_drift"]:
            direction = "BUY" if current_weight < h["target_pct"] / 100 else "SELL"
            adjust_shares = int(s["shares"] * drift * 0.3)
            if adjust_shares > 0:
                trades.append({"action": direction, "stock": name, "reason": f"Rebalance drift {drift*100:.1f}%",
                               "shares": adjust_shares, "price": s["price"], "source": "rebalance", "signal": {}})
    return trades


TRADE_ENGINES = {"ares": ares_trade, "demeter": demeter_trade, "athena": athena_trade}


# ── Main ───────────────────────────────────────────────────────────

def main():
    dry_run = "--dry-run" in sys.argv
    skip_kronos = "--skip-kronos" in sys.argv
    export_only = "--export-json" in sys.argv
    now = datetime.now(MALAYSIA_TZ)
    timestamp = now.strftime("%Y-%m-%dT%H:%M:%S+08:00")

    db = get_db()

    # Load from DB
    portfolios = load_portfolios_from_db(db)
    stock_map = load_stock_map(db)
    forecasts = {} if skip_kronos else load_kronos_forecasts()

    if export_only:
        export_json_for_web(db, portfolios)
        db.close()
        return

    # Fetch prices
    print(f"[{timestamp}] Fetching prices...")
    prices = fetch_prices(stock_map)
    print(f"  Prices: {json.dumps({k: round(v, 4) for k, v in prices.items()})}")

    # Previous prices (from last snapshot in DB)
    prev_prices = {}
    prev_snap = db.execute("SELECT holdings_json FROM portfolio_snapshots ORDER BY snapshot_at DESC LIMIT 1").fetchone()
    if prev_snap and prev_snap['holdings_json']:
        try:
            prev_holdings = json.loads(prev_snap['holdings_json'])
            prev_prices = {name: h.get('price', 0) for name, h in prev_holdings.items()}
        except Exception:
            pass

    run_record = {"timestamp": timestamp, "personas": {}, "prices": prices, "kronos": bool(forecasts)}

    for pid, persona in portfolios.items():
        # Current state from DB
        state = {"cash": persona["cash"],
                 "holdings": persona["holdings"].copy(),
                 "trade_log": []}

        snapshot = calc_portfolio_value(state["holdings"], prices, state["cash"])
        engine = TRADE_ENGINES.get(pid)
        trades = engine(persona, prices, snapshot, stock_map, prev_prices, forecasts) if engine else []

        # Save snapshot BEFORE trades (pre-trade state)
        pre_snap_id = save_snapshot(db, persona["id"], timestamp,
                                    snapshot["total"], snapshot["invested"], snapshot["cash"],
                                    snapshot["pnl"], snapshot["pnl_pct"], snapshot["stocks"])

        # Execute trades with full decision trail
        executed = []
        for t in trades:
            stock_code = stock_map.get(t["stock"], {}).get("code", t["stock"])
            ksig = t.get("signal", {})
            source = t.get("source", "unknown")

            if t["action"] == "SELL_ALL":
                sell_shares = state["holdings"][t["stock"]]["shares"]
                proceeds = sell_shares * t["price"]
                state["cash"] += proceeds
                del state["holdings"][t["stock"]]
                trade_id = save_trade(db, persona["id"], stock_code, "SELL_ALL", sell_shares, t["price"],
                                      t["reason"], ksig, source, "stop_loss" if "stop" in source else source,
                                      pre_snap_id, timestamp)
                executed.append({**t, "proceeds": round(proceeds, 2), "trade_id": trade_id})

            elif t["action"] == "SELL":
                sell_shares = min(t["shares"], state["holdings"][t["stock"]]["shares"])
                proceeds = sell_shares * t["price"]
                state["cash"] += proceeds
                state["holdings"][t["stock"]]["shares"] -= sell_shares
                if state["holdings"][t["stock"]]["shares"] <= 0:
                    del state["holdings"][t["stock"]]
                trade_id = save_trade(db, persona["id"], stock_code, "SELL", sell_shares, t["price"],
                                      t["reason"], ksig, source, source, pre_snap_id, timestamp)
                executed.append({**t, "proceeds": round(proceeds, 2), "shares": sell_shares, "trade_id": trade_id})

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
                            state["holdings"][t["stock"]] = {"shares": actual_shares, "cost": t["price"], "target_pct": 0}
                        trade_id = save_trade(db, persona["id"], stock_code, "BUY", actual_shares, t["price"],
                                              t["reason"], ksig, source, source, pre_snap_id, timestamp)
                        executed.append({**t, "cost": round(actual_cost, 2), "shares": actual_shares, "trade_id": trade_id})

        if dry_run:
            for t in trades:
                print(f"  [{pid}] WOULD {t['action']} {t['stock']}: {t['reason']}")
        else:
            # Update DB state
            update_portfolio_cash(db, persona["id"], state["cash"])
            for name, h in state["holdings"].items():
                stock_code = stock_map.get(name, {}).get("code", name)
                update_holding(db, persona["id"], stock_code, h["shares"], h["cost"], h.get("target_pct", 0))

            # Delete holdings that were sold off
            held_codes = {stock_map.get(n, {}).get("code", n) for n in state["holdings"]}
            if held_codes:
                placeholders = ','.join('?' * len(held_codes))
                db.execute(f"DELETE FROM portfolio_holdings WHERE portfolio_id=? AND stock_id NOT IN ({placeholders})",
                           [persona["id"]] + list(held_codes))
            else:
                db.execute("DELETE FROM portfolio_holdings WHERE portfolio_id=?", (persona["id"],))

            for e in executed:
                print(f"  [{pid}] #{e.get('trade_id')} {e['action']} {e['stock']} x{e.get('shares', 'ALL')} "
                      f"@ RM{e['price']}: {e['reason']}")

        # Recalculate after trades
        final_snapshot = calc_portfolio_value(state["holdings"], prices, state["cash"])
        # Save post-trade snapshot
        save_snapshot(db, persona["id"], timestamp,
                      final_snapshot["total"], final_snapshot["invested"], final_snapshot["cash"],
                      final_snapshot["pnl"], final_snapshot["pnl_pct"], final_snapshot["stocks"])

        summary = {"total": final_snapshot["total"], "invested": final_snapshot["invested"],
                   "cash": final_snapshot["cash"], "pnl": final_snapshot["pnl"],
                   "pnl_pct": final_snapshot["pnl_pct"], "holdings": final_snapshot["stocks"],
                   "trades_this_run": len(executed)}
        run_record["personas"][pid] = summary
        print(f"  [{pid}] Total: RM{final_snapshot['total']:.2f} | P&L: {final_snapshot['pnl_pct']:+.2f}% | Trades: {len(executed)}")

    db.commit()

    # Export JSON for web app
    export_json_for_web(db, portfolios)

    # Leaderboard
    print("\n═══ LEADERBOARD ═══")
    ranked = sorted(run_record["personas"].items(), key=lambda x: x[1]["pnl_pct"], reverse=True)
    medals = ["🥇", "🥈", "🥉"]
    for i, (pid, s) in enumerate(ranked):
        print(f"  {medals[i]} {pid.upper()}: RM{s['total']:.2f} ({s['pnl_pct']:+.2f}%) — {_persona_god(pid)}")

    db.close()
    return run_record


if __name__ == "__main__":
    main()
