import { useState, useMemo } from 'react'
import { Helmet } from 'react-helmet-async'
import { Calendar, ChevronLeft, ChevronRight, TrendingUp, DollarSign, PiggyBank } from 'lucide-react'
import { seo } from '../lib/seo'
import { useNavigate } from 'react-router-dom'
import ScoreBadge from '../components/ScoreBadge'
import { INDUSTRY_COLORS } from '../data/stocks'
import { useApi } from '../hooks/useApi'

interface DividendRecord {
  announceDate: string | null
  subject: string
  amount: number
  exDate: string | null
  paymentDate: string | null
}

interface DividendStock {
  stockId: string
  name: string
  industry: string
  dividendYield: number
  compositeScore: number
  status: string
  dividends: DividendRecord[]
  nextExDate: string | null
  nextAmount: number | null
}

interface DisplayStock {
  stockId: string
  name: string
  industry: string
  dividendYield: number
  compositeScore: number
  status: string
  nextExDate: string | null
  nextAmount: number | null
}

const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
]

export default function DividendCalendar() {
  const navigate = useNavigate()
  const api = useApi<DividendStock[]>('/dividends')
  const [selectedMonth, setSelectedMonth] = useState(() => new Date().getMonth())
  const [selectedYear, setSelectedYear] = useState(() => new Date().getFullYear())

  // Map API data to display format
  const calendarStocks: DisplayStock[] = useMemo(() => {
    if (!api.data || !Array.isArray(api.data)) return []

    return api.data.map(s => ({
      stockId: s.stockId,
      name: s.name,
      industry: s.industry,
      dividendYield: s.dividendYield,
      compositeScore: s.compositeScore,
      status: s.status,
      nextExDate: s.nextExDate,
      nextAmount: s.nextAmount,
    }))
  }, [api.data])

  // Sort by dividend yield descending
  const sortedStocks = useMemo(() =>
    [...calendarStocks].sort((a, b) => b.dividendYield - a.dividendYield),
    [calendarStocks]
  )

  // Group stocks into yield tiers
  const yieldTiers = useMemo(() => {
    const tiers: { label: string; min: number; max: number; color: string; stocks: DisplayStock[] }[] = [
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

  // Upcoming ex-date count (nextExDate is non-null)
  const upcomingExDates = useMemo(() =>
    sortedStocks.filter(s => s.nextExDate !== null),
    [sortedStocks]
  )

  // Navigation for month selector (for future calendar view)
  const prevMonth = () => setSelectedMonth(m => m === 0 ? 11 : m - 1)
  const nextMonth = () => setSelectedMonth(m => m === 11 ? 0 : m + 1)

  return (
    <div className="min-h-screen">
      <Helmet {...seo({
        title: 'Dividend Calendar — Divvy Bursa Tracker',
        description: 'Bursa Malaysia dividend calendar. Browse ex-dates, dividend yields, and payment schedules for KLSE stocks.',
        canonical: '/dividends',
      })} />
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
              {upcomingExDates.length > 0 ? upcomingExDates.length : '—'}
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
              Stock dividend declarations will appear here after the next scraper run.
              The pipeline checks i3investor daily for new dividend announcements.
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Active dividend stocks notice */}
            <div className="flex items-start gap-3 p-4 rounded-xl bg-emerald-50 dark:bg-emerald-950 border border-emerald-200 dark:border-emerald-800">
              <PiggyBank className="w-5 h-5 text-emerald-500 mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-sm font-medium text-emerald-800 dark:text-emerald-200">
                  {upcomingExDates.length} stocks with upcoming ex-dates
                </p>
                <p className="text-xs text-emerald-600 dark:text-emerald-400 mt-0.5">
                  Dividend data sourced from i3investor. Updated daily via automated scraper.
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
                        key={stock.stockId}
                        className="flex items-center justify-between py-3 px-4 hover:bg-white/50 dark:hover:bg-gray-900/50 transition-colors cursor-pointer"
                        onClick={() => navigate(`/stock/${stock.stockId}`)}
                      >
                        <div className="flex items-center gap-3 min-w-0">
                          <ScoreBadge score={stock.compositeScore} size="sm" />
                          <div className="min-w-0">
                            <p className="font-medium text-sm text-gray-900 dark:text-gray-100 truncate">
                              {stock.name}
                            </p>
                            <p className="text-xs text-gray-500 truncate">
                              {stock.stockId.replace('.KL', '')} · {stock.industry}
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

            {/* All stocks table view with ex-dates */}
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
                      <th className="text-right py-2 px-2">Next Ex-Date</th>
                      <th className="text-right py-2 px-4">Amount (RM)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortedStocks.map(stock => (
                      <tr
                        key={stock.stockId}
                        className="border-b border-gray-50 dark:border-gray-900 hover:bg-gray-50 dark:hover:bg-gray-900 cursor-pointer transition-colors"
                        onClick={() => navigate(`/stock/${stock.stockId}`)}
                      >
                        <td className="py-2.5 px-4">
                          <p className="font-medium text-gray-900 dark:text-gray-100">{stock.stockId.replace('.KL', '')}</p>
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
                          <ScoreBadge score={stock.compositeScore} size="sm" />
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
                        <td className="py-2.5 px-2 text-right">
                          {stock.nextExDate ? (
                            <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
                              {stock.nextExDate}
                            </span>
                          ) : (
                            <span className="text-xs text-gray-400">—</span>
                          )}
                        </td>
                        <td className="py-2.5 px-4 text-right">
                          {stock.nextAmount !== null ? (
                            <span className="text-xs text-gray-600 dark:text-gray-400">
                              {stock.nextAmount.toFixed(4)}
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
