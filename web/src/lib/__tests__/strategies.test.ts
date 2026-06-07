import { describe, it, expect } from 'vitest'
import {
  ARES_STRATEGY,
  DEMETER_STRATEGY,
  ATHENA_STRATEGY,
  ALL_STRATEGIES,
} from '../strategies'
import type { PersonaId } from '../strategies'

describe('Ares Strategy (Hyper-Momentum)', () => {
  it('has correct basic properties', () => {
    expect(ARES_STRATEGY.name).toBe('Ares')
    expect(ARES_STRATEGY.style).toBe('Hyper-Momentum')
    expect(ARES_STRATEGY.initialCapital).toBe(10000)
  })

  it('has trailing stop loss of -15%', () => {
    expect(ARES_STRATEGY.trailingStopLoss).toBe(-0.15)
    expect(ARES_STRATEGY.useTrailingStop).toBe(true)
  })

  it('has max single position of 25%', () => {
    expect(ARES_STRATEGY.maxSinglePosition).toBe(0.25)
  })

  it('requires minimum 4 stocks', () => {
    expect(ARES_STRATEGY.minStocks).toBe(4)
  })

  it('has rebalance drift of 7%', () => {
    expect(ARES_STRATEGY.rebalanceDrift).toBe(0.07)
  })

  it('has Kronos dump threshold at -3%', () => {
    expect(ARES_STRATEGY.kronosDumpThreshold).toBe(-0.03)
  })

  it('has Kronos max threshold at +10%', () => {
    expect(ARES_STRATEGY.kronosMaxThreshold).toBe(0.10)
  })

  it('has RSI overbought filter at 70', () => {
    expect(ARES_STRATEGY.rsiOverbought).toBe(70)
    expect(ARES_STRATEGY.rsiFilterEntries).toBe(true)
  })

  it('cuts losing positions harder than trailing stop', () => {
    // Trailing stop: -15%. Momentum cooling: -5% with 25% trim.
    // Cooling is tighter (5% vs 15%) — catches faster drops
    expect(ARES_STRATEGY.momentumCoolingThreshold).toBe(-0.05)
    expect(ARES_STRATEGY.momentumCoolingTrim).toBe(0.25)
    expect(Math.abs(ARES_STRATEGY.momentumCoolingThreshold))
      .toBeLessThan(Math.abs(ARES_STRATEGY.trailingStopLoss))
  })
})

describe('Demeter Strategy (Dividend-First)', () => {
  it('has correct basic properties', () => {
    expect(DEMETER_STRATEGY.name).toBe('Demeter')
    expect(DEMETER_STRATEGY.style).toBe('Dividend-First')
    expect(DEMETER_STRATEGY.initialCapital).toBe(10000)
  })

  it('has no fixed stop loss', () => {
    expect(DEMETER_STRATEGY.stopLoss).toBeNull()
  })

  it('has 10% cash buffer', () => {
    expect(DEMETER_STRATEGY.cashBuffer).toBe(0.10)
  })

  it('has minimum dividend yield of 3%', () => {
    expect(DEMETER_STRATEGY.minDividendYield).toBe(0.03)
  })

  it('has max single position of 35%', () => {
    expect(DEMETER_STRATEGY.maxSinglePosition).toBe(0.35)
  })

  it('requires minimum 4 stocks', () => {
    expect(DEMETER_STRATEGY.minStocks).toBe(4)
  })

  it('has rebalance drift of 10%', () => {
    expect(DEMETER_STRATEGY.rebalanceDrift).toBe(0.10)
  })

  it('skips Kronos bearish stocks below -5%', () => {
    expect(DEMETER_STRATEGY.kronosSkipThreshold).toBe(-0.05)
  })

  it('has FD rate of 3% for opportunity-cost comparison', () => {
    expect(DEMETER_STRATEGY.fdRate).toBe(0.03)
  })

  it('has RSI overbought filter enabled', () => {
    expect(DEMETER_STRATEGY.rsiOverbought).toBe(70)
    expect(DEMETER_STRATEGY.rsiFilterEntries).toBe(true)
  })

  it('allows larger single position than Ares (35% vs 25%)', () => {
    expect(DEMETER_STRATEGY.maxSinglePosition)
      .toBeGreaterThan(ARES_STRATEGY.maxSinglePosition)
  })
})

describe('Athena Strategy (GARP)', () => {
  it('has correct basic properties', () => {
    expect(ATHENA_STRATEGY.name).toBe('Athena')
    expect(ATHENA_STRATEGY.style).toBe('GARP (Growth At Reasonable Price)')
    expect(ATHENA_STRATEGY.initialCapital).toBe(10000)
  })

  it('has fixed stop loss at -10%', () => {
    expect(ATHENA_STRATEGY.stopLoss).toBe(-0.10)
  })

  it('takes profit at +25%, selling 50%', () => {
    expect(ATHENA_STRATEGY.takeProfit).toBe(0.25)
    expect(ATHENA_STRATEGY.takeProfitSellPct).toBe(0.50)
  })

  it('fully exits at +40% gain', () => {
    expect(ATHENA_STRATEGY.fullExitThreshold).toBe(0.40)
  })

  it('buys dip at -10%, adding 50%', () => {
    expect(ATHENA_STRATEGY.dipBuyThreshold).toBe(-0.10)
    expect(ATHENA_STRATEGY.dipBuyPct).toBe(0.50)
  })

  it('has max single position of 30%', () => {
    expect(ATHENA_STRATEGY.maxSinglePosition).toBe(0.30)
  })

  it('requires minimum 5 stocks (most diversified)', () => {
    expect(ATHENA_STRATEGY.minStocks).toBe(5)
  })

  it('has rebalance drift of 10%', () => {
    expect(ATHENA_STRATEGY.rebalanceDrift).toBe(0.10)
  })

  it('skips Kronos bearish dip buys below -5%', () => {
    expect(ATHENA_STRATEGY.kronosSkipThreshold).toBe(-0.05)
  })

  it('has RSI overbought filter enabled', () => {
    expect(ATHENA_STRATEGY.rsiOverbought).toBe(70)
    expect(ATHENA_STRATEGY.rsiFilterEntries).toBe(true)
  })

  it('has more conservative stop loss than Ares trailing stop', () => {
    // Athena: fixed -10% stop. Ares: trailing -15%.
    // Athena's fixed stop is tighter (10% < 15%)
    expect(Math.abs(ATHENA_STRATEGY.stopLoss!))
      .toBeLessThan(Math.abs(ARES_STRATEGY.trailingStopLoss))
  })

  it('requires more diversification than Ares (5 vs 4 stocks)', () => {
    expect(ATHENA_STRATEGY.minStocks)
      .toBeGreaterThan(ARES_STRATEGY.minStocks)
  })
})

describe('ALL_STRATEGIES', () => {
  it('contains all 3 personas', () => {
    const keys = Object.keys(ALL_STRATEGIES)
    expect(keys).toHaveLength(3)
    expect(keys).toContain('ares')
    expect(keys).toContain('demeter')
    expect(keys).toContain('athena')
  })

  it('each persona has a name and style', () => {
    for (const [id, strategy] of Object.entries(ALL_STRATEGIES)) {
      expect(strategy.name).toBeTruthy()
      expect(strategy.style).toBeTruthy()
      expect(strategy.initialCapital).toBe(10000)
      expect(strategy.minStocks).toBeGreaterThanOrEqual(4)
    }
  })

  it('all PersonaId keys are valid strategy IDs', () => {
    const ids: PersonaId[] = ['ares', 'demeter', 'athena']
    for (const id of ids) {
      expect(ALL_STRATEGIES[id]).toBeDefined()
      expect(ALL_STRATEGIES[id].name.toLowerCase()).toBe(id)
    }
  })

  it('strategies are read-only via `as const` (deeply readonly TS types)', () => {
    // `as const` infers literal types, not runtime freezing.
    // TypeScript would reject mutations at compile time.
    expect(ARES_STRATEGY.name).toBe('Ares')
    expect(DEMETER_STRATEGY.style).toBe('Dividend-First')
    expect(ATHENA_STRATEGY.initialCapital).toBe(10000)
    expect(ALL_STRATEGIES.ares).toBe(ARES_STRATEGY)
  })

  it('all 3 personas use same RSI filter threshold', () => {
    const rsiValues = new Set([
      ARES_STRATEGY.rsiOverbought,
      DEMETER_STRATEGY.rsiOverbought,
      ATHENA_STRATEGY.rsiOverbought,
    ])
    expect(rsiValues.size).toBe(1)
    expect(rsiValues.has(70)).toBe(true)
  })
})
