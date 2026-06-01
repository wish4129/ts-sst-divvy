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

export const stocks: Stock[] = [
  {
    code: 'MAYBANK',
    name: 'Malayan Banking Berhad',
    industry: 'Banking',
    marketCap: 120,
    lastPrice: 9.85,
    priceChange: 0.51,
    dividendYield: 6.2,
    score: { composite: 72, dividend: 32, growth: 18, quality: 16, risk: 6 },
    financials: [
      { quarter: 'Q1 2026', revenue: 15800, netIncome: 2520, freeCashFlow: 8900, peRatio: 12.8, pbRatio: 1.3, roe: 10.2, debtToEquity: 6.8, revenueGrowthYoY: 4.2 },
      { quarter: 'Q4 2025', revenue: 16200, netIncome: 2680, freeCashFlow: 7200, peRatio: 13.1, pbRatio: 1.3, roe: 10.8, debtToEquity: 6.9, revenueGrowthYoY: 5.1 },
      { quarter: 'Q3 2025', revenue: 15400, netIncome: 2490, freeCashFlow: 8100, peRatio: 13.4, pbRatio: 1.4, roe: 10.0, debtToEquity: 7.0, revenueGrowthYoY: 3.8 },
      { quarter: 'Q2 2025', revenue: 14900, netIncome: 2380, freeCashFlow: 6500, peRatio: 13.6, pbRatio: 1.4, roe: 9.8, debtToEquity: 7.1, revenueGrowthYoY: 2.9 },
    ],
    dividends: [
      { exDate: '2026-03-15', amount: 0.31, yield: 6.3 },
      { exDate: '2025-09-12', amount: 0.29, yield: 5.9 },
      { exDate: '2025-03-14', amount: 0.31, yield: 6.2 },
      { exDate: '2024-09-13', amount: 0.28, yield: 5.7 },
      { exDate: '2024-03-15', amount: 0.30, yield: 6.0 },
      { exDate: '2023-09-15', amount: 0.27, yield: 5.5 },
      { exDate: '2023-03-17', amount: 0.29, yield: 5.8 },
      { exDate: '2022-09-16', amount: 0.25, yield: 5.2 },
      { exDate: '2022-03-18', amount: 0.28, yield: 5.6 },
    ],
    status: 'active',
    addedAt: '2026-06-01',
    revisitAt: null,
    notes: '',
    sparkline: [9.80, 9.82, 9.79, 9.81, 9.83, 9.85, 9.82, 9.84, 9.86, 9.83, 9.85, 9.87, 9.84, 9.86, 9.88, 9.85, 9.83, 9.86, 9.88, 9.85, 9.87, 9.89, 9.86, 9.84, 9.87, 9.89, 9.86, 9.88, 9.85, 9.85],
  },
  {
    code: 'AXREIT',
    name: 'Axis Real Estate Investment Trust',
    industry: 'REIT',
    marketCap: 2.4,
    lastPrice: 1.82,
    priceChange: 0.31,
    dividendYield: 5.4,
    score: { composite: 68, dividend: 30, growth: 12, quality: 18, risk: 8 },
    financials: [
      { quarter: 'Q1 2026', revenue: 75, netIncome: 38, freeCashFlow: 32, peRatio: 14.2, pbRatio: 0.92, roe: 6.5, debtToEquity: 0.95, revenueGrowthYoY: 5.0 },
      { quarter: 'Q4 2025', revenue: 77, netIncome: 40, freeCashFlow: 34, peRatio: 14.0, pbRatio: 0.93, roe: 6.7, debtToEquity: 0.94, revenueGrowthYoY: 6.2 },
      { quarter: 'Q3 2025', revenue: 73, netIncome: 37, freeCashFlow: 30, peRatio: 14.5, pbRatio: 0.94, roe: 6.3, debtToEquity: 0.96, revenueGrowthYoY: 4.8 },
      { quarter: 'Q2 2025', revenue: 71, netIncome: 36, freeCashFlow: 29, peRatio: 14.8, pbRatio: 0.95, roe: 6.1, debtToEquity: 0.97, revenueGrowthYoY: 3.5 },
    ],
    dividends: [
      { exDate: '2026-05-20', amount: 0.024, yield: 5.3 },
      { exDate: '2026-02-15', amount: 0.023, yield: 5.1 },
      { exDate: '2025-11-18', amount: 0.024, yield: 5.3 },
      { exDate: '2025-08-15', amount: 0.023, yield: 5.1 },
      { exDate: '2025-05-18', amount: 0.025, yield: 5.5 },
    ],
    status: 'active',
    addedAt: '2026-06-01',
    revisitAt: null,
    notes: 'Retail REIT — occupancy recovery play. Diversified: office, industrial, retail.',
    sparkline: [1.78, 1.79, 1.80, 1.81, 1.80, 1.82, 1.81, 1.83, 1.82, 1.81, 1.80, 1.79, 1.80, 1.81, 1.82, 1.83, 1.84, 1.83, 1.82, 1.81, 1.80, 1.81, 1.82, 1.83, 1.82, 1.81, 1.80, 1.81, 1.82, 1.82],
  },
  {
    code: 'YTLPOWR',
    name: 'YTL Power International',
    industry: 'Utilities',
    marketCap: 32,
    lastPrice: 3.95,
    priceChange: 2.6,
    dividendYield: 3.2,
    score: { composite: 65, dividend: 18, growth: 26, quality: 12, risk: 9 },
    financials: [
      { quarter: 'Q1 2026', revenue: 5800, netIncome: 820, freeCashFlow: 1100, peRatio: 9.8, pbRatio: 1.8, roe: 18.5, debtToEquity: 2.1, revenueGrowthYoY: 22.0 },
      { quarter: 'Q4 2025', revenue: 5400, netIncome: 780, freeCashFlow: 950, peRatio: 10.2, pbRatio: 1.9, roe: 17.8, debtToEquity: 2.2, revenueGrowthYoY: 18.5 },
      { quarter: 'Q3 2025', revenue: 4900, netIncome: 680, freeCashFlow: 880, peRatio: 10.5, pbRatio: 2.0, roe: 16.2, debtToEquity: 2.3, revenueGrowthYoY: 15.0 },
      { quarter: 'Q2 2025', revenue: 4500, netIncome: 610, freeCashFlow: 800, peRatio: 11.0, pbRatio: 2.1, roe: 15.0, debtToEquity: 2.4, revenueGrowthYoY: 12.0 },
    ],
    dividends: [
      { exDate: '2026-05-20', amount: 0.05, yield: 2.5 },
      { exDate: '2025-11-15', amount: 0.04, yield: 2.0 },
      { exDate: '2025-05-18', amount: 0.05, yield: 2.8 },
      { exDate: '2024-11-14', amount: 0.04, yield: 2.2 },
      { exDate: '2024-05-17', amount: 0.04, yield: 2.5 },
    ],
    status: 'active',
    addedAt: '2026-06-01',
    revisitAt: null,
    notes: '',
    sparkline: [3.80, 3.82, 3.85, 3.88, 3.90, 3.92, 3.95, 3.98, 3.96, 3.94, 3.92, 3.90, 3.88, 3.85, 3.82, 3.80, 3.78, 3.82, 3.85, 3.88, 3.90, 3.95, 3.98, 4.00, 4.02, 4.00, 3.98, 3.95, 3.92, 3.95],
  },
]

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
}
