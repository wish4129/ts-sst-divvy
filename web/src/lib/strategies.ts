/**
 * Divvy persona strategy definitions for the frontend.
 *
 * Constants and display helpers for each persona's trading strategy.
 * These mirror the Python engine rules in scripts/portfolio_manager.py
 * and scripts/strategies/ares.py.
 */

export const ARES_STRATEGY = {
  name: 'Ares',
  style: 'Hyper-Momentum',
  description: 'Rides winners aggressively with trailing stop-loss protection.',
  initialCapital: 10000,

  /** Exit when drawdown from peak exceeds 15% — locks in gains from rallies */
  trailingStopLoss: -0.15,

  /** Maximum single position as fraction of portfolio */
  maxSinglePosition: 0.25,

  /** Minimum number of stocks held */
  minStocks: 4,

  /** Rebalance drift threshold */
  rebalanceDrift: 0.07,

  /** Use a trailing stop instead of a fixed stop */
  useTrailingStop: true,

  /** Kronos-driven entry — dump on Kronos < -3%, max on Kronos > 10% */
  kronosDumpThreshold: -0.03,
  kronosMaxThreshold: 0.10,

  /** RSI filter — skip BUY entries when RSI > 70 (overbought) */
  rsiOverbought: 70,
  rsiFilterEntries: true,

  /** Momentum cooling — trim on intra-session drops, unless Kronos bullish */
  momentumCoolingThreshold: -0.05,
  momentumCoolingTrim: 0.25,
} as const

export const DEMETER_STRATEGY = {
  name: 'Demeter',
  style: 'Dividend-First',
  description: 'Conservative income strategy with cash buffer and yield protection.',
  initialCapital: 10000,

  /** No fixed stop-loss — relies on yield discipline */
  stopLoss: null,

  /** Cash buffer as fraction of portfolio */
  cashBuffer: 0.10,

  /** Minimum dividend yield to hold */
  minDividendYield: 0.03,

  /** Maximum single position */
  maxSinglePosition: 0.35,

  /** Minimum stocks held */
  minStocks: 4,

  /** Rebalance drift threshold */
  rebalanceDrift: 0.10,

  /** Skip buying stocks with Kronos < -5% */
  kronosSkipThreshold: -0.05,

  /** FD rate for opportunity-cost comparison */
  fdRate: 0.03,

  /** RSI filter — skip BUY entries when RSI > 70 (overbought) */
  rsiOverbought: 70,
  rsiFilterEntries: true,
} as const

export const ATHENA_STRATEGY = {
  name: 'Athena',
  style: 'GARP (Growth At Reasonable Price)',
  description: 'Blend of growth and value with disciplined take-profit and dip-buy rules.',
  initialCapital: 10000,

  /** Fixed stop-loss */
  stopLoss: -0.10,

  /** Take profit at 25% gain, sell 50% of position */
  takeProfit: 0.25,
  takeProfitSellPct: 0.50,

  /** Full exit at 40% gain */
  fullExitThreshold: 0.40,

  /** Dip buy at -10%, buy 50% more */
  dipBuyThreshold: -0.10,
  dipBuyPct: 0.50,

  /** Maximum single position */
  maxSinglePosition: 0.30,

  /** Minimum stocks held */
  minStocks: 5,

  /** Rebalance drift threshold */
  rebalanceDrift: 0.10,

  /** Kronos confirms dip buys — skips if forecast < -5% */
  kronosSkipThreshold: -0.05,

  /** RSI filter — skip BUY entries when RSI > 70 (overbought) */
  rsiOverbought: 70,
  rsiFilterEntries: true,
} as const

export const ALL_STRATEGIES = {
  ares: ARES_STRATEGY,
  demeter: DEMETER_STRATEGY,
  athena: ATHENA_STRATEGY,
} as const

export type PersonaId = keyof typeof ALL_STRATEGIES
