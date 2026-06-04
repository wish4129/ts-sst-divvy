export interface StockScore {
  composite: number
  dividend: number
  growth: number
  quality: number
  risk: number
}

export interface StockFinancials {
  quarter: string
  revenue: number
  netIncome: number
  freeCashFlow: number
  peRatio: number
  pbRatio: number
  roe: number
  debtToEquity: number
  revenueGrowthYoY: number
}

export interface DividendRecord {
  exDate: string
  amount: number
  yield: number
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
}

export const INDUSTRY_COLORS: Record<string, string> = {
  Banking: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  Utilities: 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200',
  REIT: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
  Plantation: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  Telco: 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900 dark:text-cyan-200',
  Tech: 'bg-violet-100 text-violet-800 dark:bg-violet-900 dark:text-violet-200',
  Consumer: 'bg-pink-100 text-pink-800 dark:bg-pink-900 dark:text-pink-200',
  'Oil & Gas': 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  Healthcare: 'bg-teal-100 text-teal-800 dark:bg-teal-900 dark:text-teal-200',
  Construction: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
  'Consumer Products & Services': 'bg-pink-100 text-pink-800 dark:bg-pink-900 dark:text-pink-200',
  Automotive: 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900 dark:text-cyan-200',
  Energy: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  Packaging: 'bg-teal-100 text-teal-800 dark:bg-teal-900 dark:text-teal-200',
  Furniture: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  Industrial: 'bg-slate-100 text-slate-800 dark:bg-slate-900 dark:text-slate-200',
  Investment: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200',
  Semiconductor: 'bg-violet-100 text-violet-800 dark:bg-violet-900 dark:text-violet-200',
  Conglomerate: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200',
  Property: 'bg-lime-100 text-lime-800 dark:bg-lime-900 dark:text-lime-200',
}
