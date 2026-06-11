#!/usr/bin/env python3
"""Divvy Portfolio Manager — Supabase Postgres-backed Bursa portfolio rebalancing engine.

Three personas (Ares, Demeter, Athena) each manage configurable capital.
All trades recorded with full decision trail (reason, Kronos signal, source).
Runs hourly. Kronos 30-day AI forecasts integrated into all engines.

Usage: DB_PASSWORD=xxx python3 scripts/portfolio_manager.py [--dry-run] [--skip-kronos] [--export-json]
"""

import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

from db import get_db, dict_cursor

try:
    import yfinance as yf
except ImportError:
    print("Installing yfinance...")
    os.system(f"{sys.executable} -m pip install yfinance --quiet")
    import yfinance as yf

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from persona_db import get_all_stocks_dict, TICKER_TO_SHORT, save_persona_holdings, get_kronos_forecasts
from strategies.ares import check_trailing_stop, update_high_water_marks, TRAILING_STOP_PCT
from strategies.rsi import cached_rsi_check, clear_cache as rsi_clear_cache, RSI_OVERBOUGHT
from strategies.volume import cached_volume_check, clear_cache as volume_clear_cache, VOLUME_CONFIRM_RATIO
from strategies.sector_limits import check_sector_exposure, get_sector, SECTOR_LIMIT
HISTORY_PATH = ROOT / "web" / "public" / "portfolio_history.json"
LIVE_PRICES_PATH = ROOT / "data" / "live_prices.json"
KRONOS_PATH = ROOT / "data" / "kronos_forecast.json"
MALAYSIA_TZ = timezone(timedelta(hours=8))
LOT_SIZE = 100  # Bursa Malaysia minimum tradable lot


def round_lot(shares: int) -> int:
    """Round down to nearest lot (100 shares). Returns 0 if below 1 lot."""
    return (shares // LOT_SIZE) * LOT_SIZE

# Kevin's email for user lookup (UUID comes from Supabase Auth)
KEVIN_EMAIL = "munkevin@gmail.com"

# Resolve user ID at module load
def _get_kevin_user_id():
    """Look up Kevin's UUID from Supabase (auth.uid() may change)."""
    try:
        import sys; sys.path.insert(0, str(Path(__file__).resolve().parent))
        from db import get_db, dict_cursor
        db = get_db()
        cur = dict_cursor(db)
        cur.execute("SELECT id FROM users WHERE email=%s", (KEVIN_EMAIL,))
        row = cur.fetchone()
        cur.close()
        db.close()
        return row['id'] if row else None
    except Exception:
        return None

KEVIN_USER_ID = _get_kevin_user_id()


# ── DB helpers ─────────────────────────────────────────────────────

def load_portfolios_from_db(db, cur):
    """Load all 3 persona portfolios with holdings from Postgres."""
    # Build stock_id → short_name map from DB
    all_stocks = get_all_stocks_dict()
    code_to_name = {info['code']: sn for sn, info in all_stocks.items()}

    portfolios = {}
    cur.execute("SELECT * FROM user_portfolios WHERE user_id=%s ORDER BY persona", (KEVIN_USER_ID,))
    for row in cur.fetchall():
        pid = row['persona']
        holdings = {}
        cur.execute(
            "SELECT ph.*, s.name as stock_name FROM portfolio_holdings ph "
            "JOIN stocks s ON ph.stock_id=s.id WHERE portfolio_id=%s",
            (row['id'],)
        )
        for h in cur.fetchall():
            short = code_to_name.get(h['stock_id'], h['stock_name'])
            holdings[short] = {
                'shares': h['shares'], 'cost': float(h['avg_cost']),
                'target_pct': float(h['target_pct']),
            }
        portfolios[pid] = {
            'id': row['id'],
            'name': row['name'],
            'god': _persona_god(pid),
            'style': _persona_style(pid),
            'strategy': row['strategy'],
            'initial_capital': float(row['initial_capital']),
            'cash': float(row['cash']),
            'holdings': holdings,
            'rules': _persona_rules(pid),
        }
    return portfolios


def load_stock_map(db, cur):
    """Build {short_name: {code, name, industry, initial}} from DB."""
    return get_all_stocks_dict()


def save_trade(db, cur, portfolio_id, stock_id, action, shares, price, reason,
                kronos_signal, decision_source, triggered_by, snapshot_id, timestamp):
    """Record trade with full decision trail. Returns trade_id."""
    cur.execute(
        """INSERT INTO trades (portfolio_id, stock_id, action, shares, price, total_amount,
           reason, kronos_signal, decision_source, triggered_by, snapshot_id, executed_at)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
        (portfolio_id, stock_id, action, shares, price, shares * price,
         reason, json.dumps(kronos_signal) if kronos_signal else None,
         decision_source, triggered_by, snapshot_id, timestamp))
    return cur.fetchone()['id']


def save_snapshot(db, cur, portfolio_id, timestamp, total, invested, cash, pnl, pnl_pct, holdings):
    """Save portfolio performance snapshot. Returns snapshot_id."""
    cur.execute(
        """INSERT INTO portfolio_snapshots (portfolio_id, snapshot_at, total_value, invested,
           cash, pnl, pnl_pct, holdings_json)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
        (portfolio_id, timestamp, total, invested, cash, pnl, pnl_pct, json.dumps(holdings)))
    return cur.fetchone()['id']


def update_portfolio_cash(db, cur, portfolio_id, cash):
    cur.execute("UPDATE user_portfolios SET cash=%s, updated_at=%s WHERE id=%s",
                (cash, datetime.now(MALAYSIA_TZ).isoformat(), portfolio_id))


def sync_persona_config_cash(db, cur, portfolio_id, cash):
    """Mirror cash update to persona_config so both tables stay in sync.

    persona_config.cash is used by persona_db functions but only
    user_portfolios.cash is updated during portfolio_manager runs.
    """
    cur.execute("SELECT persona FROM user_portfolios WHERE id=%s", (portfolio_id,))
    row = cur.fetchone()
    if row:
        cur.execute("UPDATE persona_config SET cash=%s, updated_at=NOW() WHERE persona_id=%s",
                    (cash, row['persona']))


def update_holding(db, cur, portfolio_id, stock_id, shares, avg_cost, target_pct):
    if shares <= 0:
        cur.execute("DELETE FROM portfolio_holdings WHERE portfolio_id=%s AND stock_id=%s",
                    (portfolio_id, stock_id))
    else:
        cur.execute(
            """INSERT INTO portfolio_holdings (portfolio_id, stock_id, shares, avg_cost, target_pct)
               VALUES (%s,%s,%s,%s,%s)
               ON CONFLICT (portfolio_id, stock_id)
               DO UPDATE SET shares=EXCLUDED.shares, avg_cost=EXCLUDED.avg_cost,
                             target_pct=EXCLUDED.target_pct""",
            (portfolio_id, stock_id, shares, avg_cost, target_pct))


def export_json_for_web(db, cur, personas_data):
    """Export portfolio_history.json for the static web app (backward compat)."""
    history = {"runs": [], "personas": {}}
    if HISTORY_PATH.exists():
        try:
            history = json.loads(HISTORY_PATH.read_text())
        except Exception:
            pass

    cur.execute("SELECT * FROM portfolio_snapshots ORDER BY snapshot_at DESC LIMIT 50")
    snapshots = cur.fetchall()

    pid_map = {}
    cur.execute("SELECT * FROM user_portfolios WHERE user_id=%s", (KEVIN_USER_ID,))
    for pf in cur.fetchall():
        pid_map[pf['id']] = pf['persona']

    for s in snapshots:
        run = {"timestamp": s['snapshot_at'].isoformat() if hasattr(s['snapshot_at'], 'isoformat') else str(s['snapshot_at']), "personas": {}}
        snap_pid = pid_map.get(s['portfolio_id'], 'unknown')
        run["personas"][snap_pid] = {
            "total": float(s['total_value']),
            "invested": float(s['invested']),
            "cash": float(s['cash']),
            "pnl": float(s['pnl']),
            "pnl_pct": float(s['pnl_pct']),
            "holdings": json.loads(s['holdings_json']) if s['holdings_json'] else {},
            "trades_this_run": 0,
        }
        history["runs"].append(run)

    for pid, pdata in personas_data.items():
        history["personas"][pid] = {
            "cash": pdata['cash'],
            "holdings": {name: {"shares": h['shares'], "cost": h['cost']}
                         for name, h in pdata['holdings'].items()},
            "trade_log": [],
        }

    if len(history["runs"]) > 500:
        history["runs"] = history["runs"][-500:]

    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_PATH.write_text(json.dumps(history, indent=2))
    print(f"  ✓ Exported {len(history['runs'])} snapshots to portfolio_history.json")


# ── Persona metadata ────────────────────────────────────────────────

def _persona_god(pid):
    return {"ares": "God of War", "demeter": "Harvest Goddess", "athena": "Goddess of Wisdom"}.get(pid, pid)

def _persona_style(pid):
    return {"ares": "Aggressive", "demeter": "Conservative", "athena": "Hybrid"}.get(pid, pid)

def _persona_rules(pid):
    rules = {
        "ares": {"stop_loss": -0.12, "take_profit": None, "max_single_position": 0.25, "min_stocks": 4,
                 "rebalance_drift": 0.07, "cash_buffer": 0.0, "dividend_reinvest": True,
                 "momentum_cooling_threshold": -0.05, "momentum_cooling_trim": 0.25,
                 "trailing_stop_loss": -0.15, "use_trailing_stop": True,
                 "rsi_overbought": 70, "rsi_filter_entries": True,
                 "volume_confirmation_entries": True, "volume_confirmation_ratio": 1.5},
        "demeter": {"stop_loss": None, "take_profit": None, "max_single_position": 0.35, "min_stocks": 4,
                    "rebalance_drift": 0.10, "cash_buffer": 0.10, "dividend_reinvest": True,
                    "fd_rate": 0.03, "min_dividend_yield": 0.03,
                    "rsi_overbought": 70, "rsi_filter_entries": True,
                    "volume_confirmation_entries": True, "volume_confirmation_ratio": 1.5},
        "athena": {"stop_loss": -0.10, "take_profit": 0.25, "take_profit_sell_pct": 0.50,
                   "max_single_position": 0.30, "min_stocks": 5, "rebalance_drift": 0.10,
                   "dip_buy_threshold": -0.10, "dip_buy_pct": 0.50, "cash_buffer": 0.0,
                   "dividend_reinvest": True, "full_exit_threshold": 0.40, "dip_buy_cooldown_days": 30,
                   "rsi_overbought": 70, "rsi_filter_entries": True,
                   "volume_confirmation_entries": True, "volume_confirmation_ratio": 1.5},
    }
    return rules.get(pid, {})


# ── Kronos forecast integration ────────────────────────────────────

def load_kronos_forecasts():
    """Load Kronos 30-day forecasts — DB-first with JSON file fallback."""
    # Primary: read from kronos_forecasts DB table
    try:
        forecasts = get_kronos_forecasts()
        if forecasts:
            bulls = sum(1 for f in forecasts.values() if f.get("pred_change_pct", 0) > 0)
            bears = len(forecasts) - bulls
            print(f"  [Kronos] Loaded {len(forecasts)} forecasts from DB ({bulls}▲ {bears}▼)")
            return forecasts
    except Exception as e:
        print(f"  [Kronos] DB read failed: {e} — falling back to JSON file")
    # Fallback: read from kronos_forecast.json
    if not KRONOS_PATH.exists():
        print("  [Kronos] No forecast file — running without AI signals")
        return {}
    try:
        data = json.loads(KRONOS_PATH.read_text())
        forecasts = {k: v for k, v in data.items() if "error" not in v}
        bulls = sum(1 for f in forecasts.values() if f.get("pred_change_pct", 0) > 0)
        bears = len(forecasts) - bulls
        print(f"  [Kronos] Loaded {len(forecasts)} forecasts from file ({bulls}▲ {bears}▼)")
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

def calc_portfolio_value(holdings, prices, cash, initial_capital=10000):
    total_invested = sum(h["shares"] * h["cost"] for h in holdings.values())
    total_current = sum(h["shares"] * prices.get(name, h["cost"]) for name, h in holdings.items())
    total = total_current + cash
    pnl = total - initial_capital
    pnl_pct = (pnl / initial_capital) * 100 if initial_capital > 0 else 0

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

        # Session-change momentum cooling (normal intra-day detection)
        session_change = None
        if prev_prices and name in prev_prices:
            prev_price = prev_prices[name]
            if prev_price > 0:
                session_change = (s["price"] - prev_price) / prev_price

        # Cumulative-PnL fallback: when cron hasn't run for a while, session_change=0
        # but the stock is deeply underwater from cost. Detect and cool based on PnL.
        cool_triggered = False
        cool_threshold = rules.get("momentum_cooling_threshold", -0.05)
        if session_change is not None and session_change <= cool_threshold:
            cool_triggered = True
        elif pnl_pct <= cool_threshold and (session_change is None or session_change > cool_threshold):
            # PnL-based fallback: stock underwater but session_change missed it (gap in cron runs)
            # Only trigger if the drop from cost is real and we haven't cooled yet
            # Guard: don't re-cool if already trimmed this stock today
            already_trimmed = any(
                t["stock"] == name and t["source"] == "momentum_cooling"
                for t in trades
            )
            if not already_trimmed:
                cool_triggered = True
                session_change = pnl_pct  # use PnL as the "session change" for logging

        if cool_triggered:
            trim_pct = rules.get("momentum_cooling_trim", 0.25)
            change_pct = session_change if session_change is not None else pnl_pct
            if ksig["direction"] == "bullish" and ksig["change_pct"] >= 5:
                trim_pct *= 0.3
                reason = f"Momentum cool {change_pct*100:.1f}% (reduced trim — Kronos +{ksig['change_pct']:.1f}%)"
            else:
                reason = f"Momentum cool {change_pct*100:.1f}% (trim {rules['momentum_cooling_trim']*100:.0f}%)"
            trim_shares = int(s["shares"] * trim_pct)
            # Floor at 1 lot: Kronos-bullish can reduce below 100
            if trim_shares < LOT_SIZE and trim_shares > 0:
                trim_shares = LOT_SIZE
                reason += " (floored to 1 lot)"
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

        # Trailing stop: exit when drawdown from peak exceeds threshold
        if rules.get("use_trailing_stop"):
            trailing_pct = abs(rules.get("trailing_stop_loss", -0.15))
            peak = s.get("peak_price", s["price"])
            if peak > 0:
                drawdown = (s["price"] - peak) / peak
                if drawdown <= -trailing_pct:
                    trades.append({
                        "action": "SELL_ALL", "stock": name,
                        "reason": f"Trailing stop: {drawdown*100:.1f}% from peak RM{peak:.3f} (≥{trailing_pct*100:.0f}%)",
                        "shares": s["shares"], "price": s["price"],
                        "source": "trailing_stop", "signal": ksig,
                    })
                    continue  # Skip fixed stop-loss check if trailing stop triggered

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
            # RSI filter: skip BUY when RSI is overbought
            if direction == "BUY" and rules.get("rsi_filter_entries"):
                stock_info = stock_map.get(name, {})
                ticker = stock_info.get("code", "")
                if ticker:
                    skip, rsi = cached_rsi_check(ticker)
                    if skip:
                        print(f"  [Ares] Skipping BUY {name}: RSI {rsi:.0f} ≥ {rules['rsi_overbought']} (overbought)")
                        continue
            # Volume confirmation: skip BUY when volume < 1.5x 20-day avg
            if direction == "BUY" and rules.get("volume_confirmation_entries"):
                stock_info = stock_map.get(name, {})
                ticker = stock_info.get("code", "")
                if ticker:
                    confirmed, latest_vol, avg_vol = cached_volume_check(ticker)
                    if not confirmed:
                        vol_msg = f"vol {latest_vol:.0f}" if latest_vol else "no data"
                        avg_msg = f"avg {avg_vol:.0f}" if avg_vol else "N/A"
                        print(f"  [Ares] Skipping BUY {name}: low volume ({vol_msg} vs {avg_msg})")
                        continue
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
                # RSI filter: skip BUY when RSI is overbought
                if rules.get("rsi_filter_entries"):
                    stock_info = stock_map.get(best_name, {})
                    ticker = stock_info.get("code", "")
                    if ticker:
                        skip, rsi = cached_rsi_check(ticker)
                        if skip:
                            print(f"  [Demeter] Skipping BUY {best_name}: RSI {rsi:.0f} ≥ {rules['rsi_overbought']} (overbought)")
                            shares = 0  # suppress trade
                # Volume confirmation: skip BUY when volume < 1.5x 20-day avg
                if shares > 0 and rules.get("volume_confirmation_entries"):
                    stock_info = stock_map.get(best_name, {})
                    ticker = stock_info.get("code", "")
                    if ticker:
                        confirmed, latest_vol, avg_vol = cached_volume_check(ticker)
                        if not confirmed:
                            vol_msg = f"vol {latest_vol:.0f}" if latest_vol else "no data"
                            avg_msg = f"avg {avg_vol:.0f}" if avg_vol else "N/A"
                            print(f"  [Demeter] Skipping BUY {best_name}: low volume ({vol_msg} vs {avg_msg})")
                            shares = 0  # suppress trade
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
                # RSI filter: skip BUY when RSI is overbought
                if rules.get("rsi_filter_entries"):
                    stock_info = stock_map.get(name, {})
                    ticker = stock_info.get("code", "")
                    if ticker:
                        skip, rsi = cached_rsi_check(ticker)
                        if skip:
                            print(f"  [Athena] Skipping dip buy {name}: RSI {rsi:.0f} ≥ {rules['rsi_overbought']} (overbought)")
                            buy_shares = 0  # suppress trade
                # Volume confirmation: skip BUY when volume < 1.5x 20-day avg
                if buy_shares > 0 and rules.get("volume_confirmation_entries"):
                    stock_info = stock_map.get(name, {})
                    ticker = stock_info.get("code", "")
                    if ticker:
                        confirmed, latest_vol, avg_vol = cached_volume_check(ticker)
                        if not confirmed:
                            vol_msg = f"vol {latest_vol:.0f}" if latest_vol else "no data"
                            avg_msg = f"avg {avg_vol:.0f}" if avg_vol else "N/A"
                            print(f"  [Athena] Skipping dip buy {name}: low volume ({vol_msg} vs {avg_msg})")
                            buy_shares = 0  # suppress trade
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
    cur = dict_cursor(db)

    try:
        portfolios = load_portfolios_from_db(db, cur)
        stock_map = load_stock_map(db, cur)
        forecasts = {} if skip_kronos else load_kronos_forecasts()

        if export_only:
            export_json_for_web(db, cur, portfolios)
            return

        # Fetch prices
        print(f"[{timestamp}] Fetching prices...")
        prices = fetch_prices(stock_map)
        print(f"  Prices: {json.dumps({k: round(v, 4) for k, v in prices.items()})}")

        # Clear RSI and volume caches for this run
        rsi_clear_cache()
        volume_clear_cache()

        run_record = {"timestamp": timestamp, "personas": {}, "prices": prices, "kronos": bool(forecasts)}

        for pid, persona in portfolios.items():
            # Previous prices (from last snapshot of THIS persona)
            prev_prices = {}
            cur.execute(
                "SELECT holdings_json FROM portfolio_snapshots WHERE portfolio_id=%s "
                "ORDER BY snapshot_at DESC LIMIT 1",
                (persona["id"],)
            )
            prev_snap = cur.fetchone()
            if prev_snap and prev_snap['holdings_json']:
                try:
                    prev_holdings = json.loads(prev_snap['holdings_json'])
                    prev_prices = {name: h.get('price', 0) for name, h in prev_holdings.items()}
                except Exception:
                    pass

            state = {"cash": persona["cash"],
                     "holdings": {k: v.copy() for k, v in persona["holdings"].items()},
                     "trade_log": []}

            snapshot = calc_portfolio_value(state["holdings"], prices, state["cash"], persona["initial_capital"])

            # Inject trailing stop peak prices for Ares
            if pid == "ares" and persona["rules"].get("use_trailing_stop"):
                try:
                    hwm = update_high_water_marks(pid, state["holdings"], prices)
                    for name in snapshot["stocks"]:
                        if name in hwm:
                            snapshot["stocks"][name]["peak_price"] = hwm[name]
                except Exception as e:
                    print(f"  [Ares] High water mark update failed: {e}")

            engine = TRADE_ENGINES.get(pid)
            trades = engine(persona, prices, snapshot, stock_map, prev_prices, forecasts) if engine else []

            # Enforce Bursa lot size: round all shares down to nearest 100, skip sub-lot trades
            normalized = []
            for t in trades:
                lot_shares = round_lot(t["shares"])
                if lot_shares < LOT_SIZE:
                    continue  # skip odd lots
                t["shares"] = lot_shares
                normalized.append(t)
            trades = normalized

            pre_snap_id = None
            if not dry_run:
                pre_snap_id = save_snapshot(db, cur, persona["id"], timestamp,
                                        snapshot["total"], snapshot["invested"], snapshot["cash"],
                                        snapshot["pnl"], snapshot["pnl_pct"], snapshot["stocks"])

            executed = []
            for t in trades:
                stock_code = stock_map.get(t["stock"], {}).get("code", t["stock"])
                ksig = t.get("signal", {})
                source = t.get("source", "unknown")

                if t["action"] == "SELL_ALL":
                    sell_shares = round_lot(state["holdings"][t["stock"]]["shares"])
                    if sell_shares < LOT_SIZE:
                        continue
                    proceeds = sell_shares * t["price"]
                    state["cash"] += proceeds
                    # If rounded down, reduce instead of deleting
                    remaining = state["holdings"][t["stock"]]["shares"] - sell_shares
                    if remaining < LOT_SIZE:
                        del state["holdings"][t["stock"]]
                    else:
                        state["holdings"][t["stock"]]["shares"] = remaining
                    trade_id = save_trade(db, cur, persona["id"], stock_code, "SELL_ALL", sell_shares, t["price"],
                                          t["reason"], ksig, source, "stop_loss" if "stop" in source else source,
                                          pre_snap_id, timestamp)
                    executed.append({**t, "proceeds": round(proceeds, 2), "trade_id": trade_id})

                elif t["action"] == "SELL":
                    sell_shares = round_lot(min(t["shares"], state["holdings"][t["stock"]]["shares"]))
                    if sell_shares < LOT_SIZE:
                        continue
                    proceeds = sell_shares * t["price"]
                    state["cash"] += proceeds
                    state["holdings"][t["stock"]]["shares"] -= sell_shares
                    if state["holdings"][t["stock"]]["shares"] <= 0:
                        del state["holdings"][t["stock"]]
                    trade_id = save_trade(db, cur, persona["id"], stock_code, "SELL", sell_shares, t["price"],
                                          t["reason"], ksig, source, source, pre_snap_id, timestamp)
                    executed.append({**t, "proceeds": round(proceeds, 2), "shares": sell_shares, "trade_id": trade_id})

                elif t["action"] == "BUY":
                    # Sector exposure limit check
                    proposed_val = t["shares"] * t["price"]
                    if not check_sector_exposure(pid, t["stock"], proposed_val,
                                                  state["holdings"], prices, state["cash"]):
                        target_sector = get_sector(t["stock"])
                        print(f"  [{pid}] Sector limit ({SECTOR_LIMIT*100:.0f}%): skipping BUY {t['stock']} ({target_sector})")
                        continue
                    cost = t["shares"] * t["price"]
                    if cost <= state["cash"] * 1.05:
                        actual_shares = round_lot(min(t["shares"], int(state["cash"] / t["price"])))
                        if actual_shares < LOT_SIZE:
                            continue
                        actual_cost = actual_shares * t["price"]
                        state["cash"] -= actual_cost
                        if t["stock"] in state["holdings"]:
                            old = state["holdings"][t["stock"]]
                            total_shares = old["shares"] + actual_shares
                            old["cost"] = ((old["cost"] * old["shares"]) + actual_cost) / total_shares
                            old["shares"] = total_shares
                        else:
                            state["holdings"][t["stock"]] = {"shares": actual_shares, "cost": t["price"], "target_pct": 0}
                        trade_id = save_trade(db, cur, persona["id"], stock_code, "BUY", actual_shares, t["price"],
                                              t["reason"], ksig, source, source, pre_snap_id, timestamp)
                        executed.append({**t, "cost": round(actual_cost, 2), "shares": actual_shares, "trade_id": trade_id})

            if dry_run:
                for t in trades:
                    print(f"  [{pid}] WOULD {t['action']} {t['stock']}: {t['reason']}")
            else:
                update_portfolio_cash(db, cur, persona["id"], state["cash"])
                sync_persona_config_cash(db, cur, persona["id"], state["cash"])
                for name, h in state["holdings"].items():
                    stock_code = stock_map.get(name, {}).get("code", name)
                    update_holding(db, cur, persona["id"], stock_code, h["shares"], h["cost"], h.get("target_pct", 0))

                # Delete holdings that were sold off
                held_codes = {stock_map.get(n, {}).get("code", n) for n in state["holdings"]}
                if held_codes:
                    cur.execute(
                        "DELETE FROM portfolio_holdings WHERE portfolio_id=%s AND stock_id NOT IN %s",
                        (persona["id"], tuple(held_codes)))
                else:
                    cur.execute("DELETE FROM portfolio_holdings WHERE portfolio_id=%s", (persona["id"],))

                db.commit()

            run_record["personas"][pid] = {
                "snapshot": snapshot, "trades": executed, "state": state,
            }

        export_json_for_web(db, cur, portfolios)

        summary = {pid: f"{v['snapshot']['pnl_pct']:+.1f}% ({len(v['trades'])} trades)"
                   for pid, v in run_record["personas"].items()}
        print(f"[{timestamp}] Done: {summary}")

    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        raise
    finally:
        cur.close()
        db.close()


if __name__ == "__main__":
    main()
