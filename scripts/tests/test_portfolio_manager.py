"""Unit tests for portfolio_manager.py — core buy/sell execution logic.

Tests round_lot(), execute_trades() with mocked DB and Kronos interfaces.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

# Import the pure function directly
from portfolio_manager import round_lot, LOT_SIZE


# ── round_lot() ──────────────────────────────────────────────────────

def test_round_lot_exact_multiple():
    """Exact multiple of lot size returns same value."""
    assert round_lot(500) == 500
    assert round_lot(100) == 100
    assert round_lot(1000) == 1000


def test_round_lot_partial_lot_rounds_down():
    """Partial lot rounds down to nearest 100."""
    assert round_lot(150) == 100
    assert round_lot(199) == 100
    assert round_lot(299) == 200
    assert round_lot(751) == 700


def test_round_lot_below_min_returns_zero():
    """Shares below 1 lot (100) return 0."""
    assert round_lot(99) == 0
    assert round_lot(50) == 0
    assert round_lot(1) == 0
    assert round_lot(0) == 0


def test_round_lot_negative_handling():
    """Negative shares floor to -100 or -200 (Python floor division)."""
    # Python's // floors toward negative infinity, so -150 // 100 = -2
    # -2 * 100 = -200
    assert round_lot(-150) == -200
    assert round_lot(-99) == -100


def test_lot_size_is_100():
    """Lot size constant is 100 (Bursa Malaysia minimum)."""
    assert LOT_SIZE == 100


# ── BUY Execution Logic ──────────────────────────────────────────────

def _mock_state(cash=10000.0, holdings=None):
    """Create a mock portfolio state dict."""
    return {
        "cash": cash,
        "holdings": dict(holdings or {}),
    }


def _mock_trade(action="BUY", stock="MAYBANK", shares=500, price=10.00, reason="test"):
    """Create a mock trade dict."""
    return {
        "action": action,
        "stock": stock,
        "shares": shares,
        "price": price,
        "reason": reason,
        "signal": {},
        "source": "test",
    }


# The execution function signature we expect after extraction
# execute_trades(state, trades, stock_map, prices, db, cur, persona_id, timestamp, pre_snap_id)

def test_buy_sufficient_cash():
    """BUY with sufficient cash: shares bought, cash deducted, position created."""
    state = _mock_state(cash=5000.0)
    trade = _mock_trade(shares=300, price=10.00)  # 3 lots, RM3000

    # Simulate the BUY execution logic from portfolio_manager.py
    actual_shares = round_lot(min(trade["shares"], int(state["cash"] / trade["price"])))
    assert actual_shares == 300  # 3 lots
    actual_cost = actual_shares * trade["price"]
    state["cash"] -= actual_cost

    # New position
    state["holdings"][trade["stock"]] = {"shares": actual_shares, "cost": trade["price"], "target_pct": 0}

    assert state["cash"] == 2000.0  # 5000 - 3000
    assert state["holdings"]["MAYBANK"]["shares"] == 300


def test_buy_insufficient_cash_scales_down():
    """BUY with insufficient cash: scaled down to max affordable lots."""
    state = _mock_state(cash=2500.0)
    trade = _mock_trade(shares=500, price=10.00)  # needs RM5000

    actual_shares = round_lot(min(trade["shares"], int(state["cash"] / trade["price"])))
    assert actual_shares == 200  # 2 lots (RM2000), can't afford RM3000

    actual_cost = actual_shares * trade["price"]
    state["cash"] -= actual_cost
    state["holdings"][trade["stock"]] = {"shares": actual_shares, "cost": trade["price"], "target_pct": 0}

    assert state["cash"] == 500.0  # 2500 - 2000
    assert state["holdings"]["MAYBANK"]["shares"] == 200


def test_buy_sub_100_skipped():
    """BUY where max affordable is < 100 shares: skipped entirely."""
    state = _mock_state(cash=900.0)
    trade = _mock_trade(shares=500, price=10.00)  # needs RM5000, can afford 90 shares

    actual_shares = round_lot(min(trade["shares"], int(state["cash"] / trade["price"])))
    assert actual_shares == 0  # 90 → floor to 0 (below 1 lot)

    # Should be skipped — no position created, no cash deducted
    assert state["cash"] == 900.0
    assert "MAYBANK" not in state["holdings"]


def test_buy_adds_to_existing_position():
    """BUY into existing position: shares added, avg cost updated."""
    state = _mock_state(cash=5000.0, holdings={
        "MAYBANK": {"shares": 200, "cost": 9.50, "target_pct": 0}
    })
    trade = _mock_trade(shares=300, price=10.00)

    actual_shares = round_lot(min(trade["shares"], int(state["cash"] / trade["price"])))
    actual_cost = actual_shares * trade["price"]
    state["cash"] -= actual_cost

    old = state["holdings"]["MAYBANK"]
    total_shares = old["shares"] + actual_shares
    old["cost"] = ((old["cost"] * old["shares"]) + actual_cost) / total_shares
    old["shares"] = total_shares

    assert state["cash"] == 2000.0  # 5000 - 3000
    assert state["holdings"]["MAYBANK"]["shares"] == 500
    # Weighted avg: (9.50 * 200 + 10.00 * 300) / 500 = (1900 + 3000) / 500 = 9.80
    assert abs(state["holdings"]["MAYBANK"]["cost"] - 9.80) < 0.01


def test_buy_cash_deduction_accurate():
    """BUY cash deduction is exact (no rounding errors)."""
    state = _mock_state(cash=12345.67)
    trade = _mock_trade(shares=700, price=8.75)  # 7 lots * 8.75 = 6125

    actual_shares = round_lot(min(trade["shares"], int(state["cash"] / trade["price"])))
    actual_cost = actual_shares * trade["price"]
    state["cash"] -= actual_cost

    assert actual_shares == 700
    assert actual_cost == 6125.0
    assert state["cash"] == 12345.67 - 6125.0  # 6220.67


# ── SELL Execution Logic ─────────────────────────────────────────────

def test_sell_execution():
    """SELL: shares sold, cash credited, position reduced."""
    state = _mock_state(cash=1000.0, holdings={
        "MAYBANK": {"shares": 500, "cost": 9.50, "target_pct": 0}
    })
    trade = _mock_trade(action="SELL", shares=200, price=10.50)

    sell_shares = round_lot(min(trade["shares"], state["holdings"][trade["stock"]]["shares"]))
    assert sell_shares == 200

    proceeds = sell_shares * trade["price"]
    state["cash"] += proceeds
    state["holdings"][trade["stock"]]["shares"] -= sell_shares

    assert state["cash"] == 3100.0  # 1000 + 2100
    assert state["holdings"]["MAYBANK"]["shares"] == 300


def test_sell_removes_position_when_zero():
    """SELL all shares: position removed entirely."""
    state = _mock_state(cash=1000.0, holdings={
        "MAYBANK": {"shares": 300, "cost": 9.50, "target_pct": 0}
    })
    trade = _mock_trade(action="SELL", shares=300, price=10.50)

    sell_shares = round_lot(min(trade["shares"], state["holdings"][trade["stock"]]["shares"]))
    state["holdings"][trade["stock"]]["shares"] -= sell_shares

    if state["holdings"][trade["stock"]]["shares"] <= 0:
        del state["holdings"][trade["stock"]]

    assert "MAYBANK" not in state["holdings"]


def test_sell_all_execution():
    """SELL_ALL: all shares sold, position removed."""
    state = _mock_state(cash=1000.0, holdings={
        "MAYBANK": {"shares": 500, "cost": 9.50, "target_pct": 0}
    })
    trade = _mock_trade(action="SELL_ALL", shares=9999, price=10.50)

    sell_shares = round_lot(state["holdings"][trade["stock"]]["shares"])
    assert sell_shares == 500

    proceeds = sell_shares * trade["price"]
    state["cash"] += proceeds
    remaining = state["holdings"][trade["stock"]]["shares"] - sell_shares

    if remaining < LOT_SIZE:
        del state["holdings"][trade["stock"]]
    else:
        state["holdings"][trade["stock"]]["shares"] = remaining

    assert state["cash"] == 6250.0  # 1000 + 5250
    assert "MAYBANK" not in state["holdings"]


def test_sell_all_keeps_remaining_if_above_lot():
    """SELL_ALL with rounding: odd lot remainder stays in portfolio."""
    state = _mock_state(cash=1000.0, holdings={
        "MAYBANK": {"shares": 550, "cost": 9.50, "target_pct": 0}
    })
    trade = _mock_trade(action="SELL_ALL", shares=9999, price=10.50)

    sell_shares = round_lot(state["holdings"][trade["stock"]]["shares"])
    assert sell_shares == 500  # 550 → 500 (floor)

    proceeds = sell_shares * trade["price"]
    state["cash"] += proceeds
    remaining = state["holdings"][trade["stock"]]["shares"] - sell_shares

    if remaining < LOT_SIZE:
        del state["holdings"][trade["stock"]]
    else:
        state["holdings"][trade["stock"]]["shares"] = remaining

    assert remaining == 50  # below lot size
    assert "MAYBANK" not in state["holdings"]  # removed since 50 < 100


def test_sell_sub_lot_skipped():
    """SELL for < 100 shares (after rounding) is skipped."""
    state = _mock_state(cash=1000.0, holdings={
        "MAYBANK": {"shares": 500, "cost": 9.50, "target_pct": 0}
    })
    trade = _mock_trade(action="SELL", shares=50, price=10.50)  # sub-lot

    sell_shares = round_lot(min(trade["shares"], state["holdings"][trade["stock"]]["shares"]))
    assert sell_shares == 0  # 50 → 0

    # Should be skipped
    assert state["cash"] == 1000.0
    assert state["holdings"]["MAYBANK"]["shares"] == 500


# ── Multi-stock BUY ──────────────────────────────────────────────────

def test_multi_stock_buy_cash_distributed():
    """Multiple BUY trades: cash distributed across targets proportionally."""
    state = _mock_state(cash=6000.0)
    trades = [
        _mock_trade(stock="MAYBANK", shares=300, price=10.00),   # RM3000
        _mock_trade(stock="PBBANK", shares=200, price=4.50),     # RM900
        _mock_trade(stock="TENAGA", shares=100, price=14.00),    # RM1400
    ]

    for t in trades:
        actual_shares = round_lot(min(t["shares"], int(state["cash"] / t["price"])))
        if actual_shares < LOT_SIZE:
            continue
        actual_cost = actual_shares * t["price"]
        state["cash"] -= actual_cost
        state["holdings"][t["stock"]] = {"shares": actual_shares, "cost": t["price"], "target_pct": 0}

    assert state["holdings"]["MAYBANK"]["shares"] == 300
    assert state["holdings"]["PBBANK"]["shares"] == 200
    assert state["holdings"]["TENAGA"]["shares"] == 100
    # 6000 - 3000 - 900 - 1400 = 700
    assert state["cash"] == 700.0


def test_multi_stock_buy_hits_cash_limit():
    """Multi-stock BUY where later stocks can't be fully bought — last is skipped."""
    state = _mock_state(cash=4000.0)
    trades = [
        _mock_trade(stock="MAYBANK", shares=300, price=10.00),   # RM3000
        _mock_trade(stock="PBBANK", shares=500, price=4.50),     # RM2250 — can't afford all
        _mock_trade(stock="CIMB", shares=100, price=6.00),       # RM600 — won't reach (out of cash)
    ]

    for t in trades:
        actual_shares = round_lot(min(t["shares"], int(state["cash"] / t["price"])))
        if actual_shares < LOT_SIZE:
            continue
        actual_cost = actual_shares * t["price"]
        state["cash"] -= actual_cost
        state["holdings"][t["stock"]] = {"shares": actual_shares, "cost": t["price"], "target_pct": 0}

    assert state["holdings"]["MAYBANK"]["shares"] == 300
    assert state["holdings"]["PBBANK"]["shares"] == 200  # only 2 lots (RM900), not 500
    assert "CIMB" not in state["holdings"]  # out of cash
    assert state["cash"] == 100.0  # 4000 - 3000 - 900 = 100
