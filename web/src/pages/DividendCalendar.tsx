import { useState, useMemo } from 'react'
import { Calendar, ChevronLeft, ChevronRight, TrendingUp, DollarSign } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import ScoreBadge from '../components/ScoreBadge'
import { INDUSTRY_COLORS, stocks as staticStocks } from '../data/stocks'
import { useApi } from '../hooks/useApi'
import type { Stock } from '../data/stocks'

interface WatchlistStock {
  code: string
  name: string
  industry: string
  lastPrice: number
  status: 'active' | 'revisit' | 'removed'
  compositeScore: number
  hasAiReport: boolean
}

const TICKER_MAP: Record<string, string> = {
  'MAYBANK': '1155.KL', 'YTLPOWR': '6742.KL', 'AXREIT': '5106.KL',
  'INSAS': '3379.KL', 'LIIHEN': '7089.KL', 'SCIENTEX': '4731.KL',
  'GENETEC': '0104.KL', 'KLK': '2445.KL', 'INARI': '0166.KL',
  'SIME': '4197.KL', 'MAGNI': '7087.KL', 'MBMR': '5983.KL',
  'AME': '5293.KL', 'DELEUM': '5132.KL', 'WASCO': '5142.KL',
  'KIPREIT': '5280.KL', 'INTA': 'INTA.KL',
  'RHB': '1066.KL', 'PADINI': '7052.KL',
  'GAMUDA': '5398.KL', 'MATRIX': '5236.KL',
  'PBBANK': '1295.KL', 'TIME': '5031.KL', 'SCICOM': '0099.KL',
  'SEM': '5250.KL',
}

const TICKER_TO_SHORT: Record<string, string> = {}
for (const [short, ticker] of Object.entries(TICKER_MAP)) {
  TICKER_TO_SHORT[ticker] = short
}

interface CalendarStock {
  code: string
  ticker: string
  name: string
  industry: string
  dividendYield: number
  score: number
  status: string
  exDate: string | null
  amount: number | null
}

const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
]

export default function DividendCalendar() {
  const navigate = useNavigate()
  const api = useApi<WatchlistStock[]>('/watchlist')
  const [selectedMonth, setSelectedMonth] = useState(() => new Date().getMonth())
  const [selectedYear] = useState(() => new Date().getFullYear())

  // Merge API data with static for dividend yield
  const calendarStocks: CalendarStock[] = useMemo(() => {
    if (!api.data || !Array.isArray(api.data)) return []

    const tickerToShort: Record<string, string> = {}
    for (const [short, ticker] of Object.entries(TICKER_MAP)) {
      tickerToShort[ticker] = short
    }

    return api.data.map(s => {
      const shortCode = tickerToShort[s.code] || s.code
      const existing = staticStocks.find(st => st.code === shortCode)
      return {
        code: s.code,
        ticker: shortCode,
        name: s.name || existing?.name || shortCode,
        industry: s.industry || existing?.industry || '',
        dividendYield: existing?.dividendYield || 0,
        score: s.compositeScore,
        status: s.compositeScore >= 70 ? 'active' : 'revisit',
        exDate: null,
        amount: null,
      }
    }).filter(s => s.dividendYield > 0)
  }, [api.data])

  // Sort by dividend yield descending
  const sortedStocks = useMemo(() =>
    [...calendarStocks].sort((a, b) => b.dividendYield - a.dividendYield),
    [calendarStocks]
  )

  // Group stocks into yield tiers for the "calendar" view
  const yieldTiers = useMemo(() => {
    const tiers: { label: string; min: number; max: number; color: string; stocks: CalendarStock[] }[] = [
      { label: '8%+ High Yield', min: 8, max: Infinity, color: 'border-emerald-400 bg-emerald-50 dark:bg-emerald-950', stocks: [] },
      { label: '5%–8% Yield', min: 5, max: 8, color: 'border-blue-400 bg-blue-50 dark:bg-blue-950', stocks: [] },
      { label: '3%–5% Yield', min: 3, max: 5, color: 'border-amber-400 bg-amber-50 dark:bg-amber-950', stocks: [] },
      { label: 'Below 3%', min: 0, max: 3, color: 'border-gray-300 bg-gray-50 dark:bg-gray-900', stocks: [] },
    ]
    for (const s of sortedStocks) {
      for (const tier of tiers) {
        if (s.dividendYield >= tier.min && s.dividendYield < tier.max) {
          tier.stocks.push(s)
          break
        }
      }
    }
    return tiers.filter(t => t.stocks.length > 0)
  }, [sortedStocks])

  const totalYield = useMemo(() =>
    calendarStocks.reduce((sum, s) => sum + s.dividendYield, 0),
    [calendarStocks]
  )
  const avgYield = calendarStocks.length > 0
    ? totalYield / calendarStocks.length
    : 0

  // Navigation for month selector
  const prevMonth = () => setSelectedMonth(m => m === 0 ? 11 : m - 1)
  const nextMonth = () => setSelectedMonth(m => m === 11 ? 0 : m + 1)

  return (
    <div className="min-h-screen">
      <main className="max-w-4xl mx-auto px-4 py-6">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            Dividend Calendar
          </h1>
          <div className="flex items-center gap-1">
            <button
              onClick={prevMonth}
              aria-label="Previous month"
              className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300 w-32 text-center">
              {MONTHS[selectedMonth]} {selectedYear}
            </span>
            <button
              onClick={nextMonth}
              aria-label="Next month"
              className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Summary cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          <div className="p-3 rounded-xl border border-gray-200 dark:border-gray-800">
            <p className="text-xs text-gray-500 mb-1">Stocks with Yield</p>
            <p className="text-xl font-bold text-gray-900 dark:text-gray-100">{calendarStocks.length}</p>
          </div>
          <div className="p-3 rounded-xl border border-gray-200 dark:border-gray-800">
            <p className="text-xs text-gray-500 mb-1">Avg Dividend Yield</p>
            <p className="text-xl font-bold text-emerald-600 dark:text-emerald-400">
              {avgYield.toFixed(1)}%
            </p>
          </div>
          <div className="p-3 rounded-xl border border-gray-200 dark:border-gray-800">
            <p className="text-xs text-gray-500 mb-1">Highest Yield</p>
            <p className="text-xl font-bold text-emerald-600 dark:text-emerald-400">
              {sortedStocks.length > 0 ? sortedStocks[0].dividendYield.toFixed(1) + '%' : '—'}
            </p>
          </div>
          <div className="p-3 rounded-xl border border-gray-200 dark:border-gray-800">
            <p className="text-xs text-gray-500 mb-1">Upcoming Ex-Dates</p>
            <p className="text-xl font-bold text-gray-900 dark:text-gray-100">
              {sortedStocks.filter(s => s.exDate).length || '—'}
            </p>
          </div>
        </div>

        {api.loading ? (
          <DividendSkeleton />
        ) : calendarStocks.length === 0 ? (
          <div className="text-center py-16">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gray-100 dark:bg-gray-800 mb-4">
              <Calendar className="w-8 h-8 text-gray-400" />
            </div>
            <h3 className="text-lg font-semibold text-gray-700 dark:text-gray-300 mb-1">
              No dividend data yet
            </h3>
            <p className="text-sm text-gray-500 max-w-sm mx-auto">
              Stock dividend yields will appear here after the next pipeline run.
              Browse the universe to add more dividend-paying stocks.
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Info banner */}
            <div className="flex items-start gap-3 p-4 rounded-xl bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800">
              <DollarSign className="w-5 h-5 text-blue-500 mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-sm font-medium text-blue-800 dark:text-blue-200">
                  Ex-dates coming soon
                </p>
                <p className="text-xs text-blue-600 dark:text-blue-400 mt-0.5">
                  Currently showing stocks by dividend yield tier. Exact ex-dates will be populated by the financial data pipeline.
                </p>
              </div>
            </div>

            {/* Yield tiers */}
            {yieldTiers.map(tier => (
              <div key={tier.label}>
                <div className="flex items-center gap-2 mb-3">
                  <div className={`w-3 h-3 rounded-full border-2 ${tier.color.split(' ')[0]}`} />
                  <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                    {tier.label}
                    <span className="ml-1.5 text-xs text-gray-400 font-normal">
                      ({tier.stocks.length})
                    </span>
                  </h2>
                </div>
                <div className={`rounded-xl border ${tier.color}`}>
                  <div className="divide-y divide-gray-100 dark:divide-gray-800">
                    {tier.stocks.map(stock => (
                      <div
                        key={stock.code}
                        className="flex items-center justify-between py-3 px-4 hover:bg-white/50 dark:hover:bg-gray-900/50 transition-colors cursor-pointer"
                        onClick={() => navigate(`/stock/${stock.code}`)}
                      >
                        <div className="flex items-center gap-3 min-w-0">
                          <ScoreBadge score={stock.score} size="sm" />
                          <div className="min-w-0">
                            <p className="font-medium text-sm text-gray-900 dark:text-gray-100 truncate">
                              {stock.name}
                            </p>
                            <p className="text-xs text-gray-500 truncate">
                              {stock.ticker} · {stock.industry}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-3 flex-shrink-0">
                          <div className="text-right">
                            <p className="text-sm font-semibold text-emerald-600 dark:text-emerald-400">
                              {stock.dividendYield.toFixed(1)}%
                            </p>
                            <p className="text-[10px] text-gray-400">DY</p>
                          </div>
                          <TrendingUp className={`w-4 h-4 ${
                            stock.dividendYield >= 6 ? 'text-emerald-500' :
                            stock.dividendYield >= 3 ? 'text-amber-500' : 'text-gray-400'
                          }`} />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ))}

            {/* All stocks table view */}
            <div className="rounded-xl border border-gray-200 dark:border-gray-800 overflow-hidden">
              <div className="p-3 border-b border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900">
                <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                  All Dividend Stocks ({sortedStocks.length})
                </h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-xs text-gray-500 border-b border-gray-100 dark:border-gray-800">
                      <th className="text-left py-2 px-4">Stock</th>
                      <th className="text-left py-2 px-2 hidden md:table-cell">Industry</th>
                      <th className="text-right py-2 px-2">Score</th>
                      <th className="text-right py-2 px-2">Dividend Yield</th>
                      <th className="text-right py-2 px-4">Ex-Date</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortedStocks.map(stock => (
                      <tr
                        key={stock.code}
                        className="border-b border-gray-50 dark:border-gray-900 hover:bg-gray-50 dark:hover:bg-gray-900 cursor-pointer transition-colors"
                        onClick={() => navigate(`/stock/${stock.code}`)}
                      >
                        <td className="py-2.5 px-4">
                          <p className="font-medium text-gray-900 dark:text-gray-100">{stock.ticker}</p>
                          <p className="text-xs text-gray-500 truncate max-w-[180px]">{stock.name}</p>
                        </td>
                        <td className="py-2.5 px-2 hidden md:table-cell">
                          <span className={`px-2 py-0.5 rounded-full text-xs ${
                            INDUSTRY_COLORS[stock.industry] || 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200'
                          }`}>
                            {stock.industry}
                          </span>
                        </td>
                        <td className="py-2.5 px-2 text-right">
                          <ScoreBadge score={stock.score} size="sm" />
                        </td>
                        <td className="py-2.5 px-2 text-right">
                          <span className={`font-semibold ${
                            stock.dividendYield >= 6 ? 'text-emerald-600 dark:text-emerald-400' :
                            stock.dividendYield >= 3 ? 'text-amber-600 dark:text-amber-400' :
                            'text-gray-500'
                          }`}>
                            {stock.dividendYield.toFixed(1)}%
                          </span>
                        </td>
                        <td className="py-2.5 px-4 text-right">
                          {stock.exDate ? (
                            <span className="text-xs text-gray-600 dark:text-gray-400">
                              {stock.exDate}
                            </span>
                          ) : (
                            <span className="text-xs text-gray-400">—</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}

function DividendSkeleton() {
  const shimmer = 'bg-gray-200 dark:bg-gray-700 animate-pulse rounded'
  return (
    <div className="space-y-4">
      {Array.from({ length: 3 }).map((_, ti) => (
        <div key={ti} className="rounded-xl border border-gray-200 dark:border-gray-800 p-4">
          <div className={`h-4 w-32 ${shimmer} mb-3`} />
          <div className="space-y-2">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="flex items-center justify-between py-2">
                <div className="flex items-center gap-3">
                  <div className={`w-8 h-8 rounded-full ${shimmer}`} />
                  <div>
                    <div className={`h-4 w-24 ${shimmer} mb-1`} />
                    <div className={`h-3 w-40 ${shimmer}`} />
                  </div>
                </div>
                <div className={`h-5 w-16 ${shimmer}`} />
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
