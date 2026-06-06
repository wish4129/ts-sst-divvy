"""Backtest metrics — CAGR, Sharpe ratio, max drawdown, annualized volatility."""

import math
from typing import List


def cagr(initial: float, final: float, years: float) -> float:
    """Compound Annual Growth Rate.

    Args:
        initial: Starting portfolio value
        final: Ending portfolio value
        years: Time period in years

    Returns:
        CAGR as decimal (e.g., 0.12 = 12%)
    """
    if initial <= 0 or final <= 0 or years <= 0:
        return 0.0
    return (final / initial) ** (1.0 / years) - 1.0


def max_drawdown(daily_values: List[float]) -> float:
    """Maximum peak-to-trough decline.

    Args:
        daily_values: Chronological portfolio values (daily)

    Returns:
        Max drawdown as negative decimal (e.g., -0.25 = -25%)
    """
    if not daily_values or len(daily_values) < 2:
        return 0.0
    peak = daily_values[0]
    max_dd = 0.0
    for v in daily_values:
        if v > peak:
            peak = v
        dd = (v - peak) / peak if peak > 0 else 0.0
        if dd < max_dd:
            max_dd = dd
    return max_dd


def sharpe_ratio(daily_returns: List[float], risk_free_annual: float = 0.03, trading_days: int = 252) -> float:
    """Annualized Sharpe ratio.

    Args:
        daily_returns: List of daily returns as decimals
        risk_free_annual: Annual risk-free rate (default 3% for Malaysia OPR-implied)
        trading_days: Trading days per year (Bursa: ~245, rounded to 252 convention)

    Returns:
        Annualized Sharpe ratio
    """
    if len(daily_returns) < 2:
        return 0.0
    mean_ret = sum(daily_returns) / len(daily_returns)
    if mean_ret == 0:
        return 0.0
    # Population std
    variance = sum((r - mean_ret) ** 2 for r in daily_returns) / len(daily_returns)
    std_ret = math.sqrt(variance)
    if std_ret == 0:
        return 0.0
    daily_rf = risk_free_annual / trading_days
    return (mean_ret - daily_rf) / std_ret * math.sqrt(trading_days)


def annualized_volatility(daily_returns: List[float], trading_days: int = 252) -> float:
    """Annualized volatility from daily returns."""
    if len(daily_returns) < 2:
        return 0.0
    mean_ret = sum(daily_returns) / len(daily_returns)
    variance = sum((r - mean_ret) ** 2 for r in daily_returns) / len(daily_returns)
    return math.sqrt(variance) * math.sqrt(trading_days)


def win_rate(trades: list) -> float:
    """Percentage of winning trades."""
    if not trades:
        return 0.0
    wins = sum(1 for t in trades if t.get("pnl", 0) > 0)
    return wins / len(trades)


def profit_factor(trades: list) -> float:
    """Gross profit / gross loss."""
    gross_profit = sum(t.get("pnl", 0) for t in trades if t.get("pnl", 0) > 0)
    gross_loss = abs(sum(t.get("pnl", 0) for t in trades if t.get("pnl", 0) < 0))
    if gross_loss == 0:
        return float("inf") if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def total_return(initial: float, final: float) -> float:
    """Total return as decimal."""
    if initial <= 0:
        return 0.0
    return (final - initial) / initial
