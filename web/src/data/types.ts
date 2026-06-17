export interface StockFinancials {
  quarter: string
  revenue: number
  netIncome: number
  freeCashFlow: number
  peRatio: number
  pbRatio?: number
  roe: number
  debtToEquity: number
  revenueGrowthYoY: number
}

export interface DividendRecord {
  exDate: string
  amount: number
  yield?: number
  subject?: string
  paymentDate?: string
  announceDate?: string
}

export interface StockScore {
  composite: number
}

export interface Stock {
  code: string
  name: string
  industry: string
  marketCap: number
  lastPrice: number
  priceChange: number
  dividendYield: number
  score: StockScore
  financials: StockFinancials[]
  dividends: DividendRecord[]
  status: 'active' | 'revisit' | 'removed'
  addedAt: string
  revisitAt: string | null
  notes: string
  sparkline: number[]
  pivotTag?: string | null
}
