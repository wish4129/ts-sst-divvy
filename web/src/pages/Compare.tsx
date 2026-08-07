import { useState, useMemo, useEffect } from 'react'
import { Helmet } from 'react-helmet-async'
import { useNavigate } from 'react-router-dom'
import { GitCompare, X, Plus, ArrowRight, DollarSign, BarChart3 } from 'lucide-react'
import { seo } from '../lib/seo'
import ScoreBadge from '../components/ScoreBadge'
import { useApi } from '../hooks/useApi'
import { INDUSTRY_COLORS } from '../data/stocks'

interface WatchlistStock {
  code: string
  name: string
  industry: string
  lastPrice: number
  status: 'active' | 'revisit' | 'removed'
  compositeScore: number
  hasAiReport: boolean
  peRatio: number | null
  dividendYield: number | null
  roe: number | null
  debtToEquity: number | null
  marketCap: number | null
}

interface AnalysisData {
  stock_name: string
  industry: string
  score_composite: number
  score_breakdown: Record<string, number> | null
  kronos_signal: Record<string, any> | null
  ai_report: Record<string, string> | null
  rationale: Record<string, any> | null
}

interface ComparisonStock extends WatchlistStock {
  analysis?: AnalysisData
}

const API_URL = import.meta.env.VITE_API_URL || ''
const MAX_COMPARE = 3

function MetricRow({ label, icon: Icon, values, format, highlight }: {
  label: string
  icon?: React.ComponentType<{ className?: string }>
  values: (string | number)[]
  format?: (v: string | number) => string
  highlight?: boolean
}) {
  return (
    <tr className={highlight ? 'bg-emerald-50/50 dark:bg-emerald-950/20' : ''}>
      <td className="py-3 px-4 font-medium text-sm text-gray-600 dark:text-gray-400 whitespace-nowrap">
        <span className="flex items-center gap-1.5">
          {Icon && <Icon className="w-3.5 h-3.5" />}
          {label}
        </span>
      </td>
      {values.map((v, i) => (
        <td key={i} className={`py-3 px-4 text-sm text-center ${highlight ? 'font-semibold text-emerald-700 dark:text-emerald-400' : 'text-gray-900 dark:text-gray-100'}`}>
          {format ? format(v) : v}
        </td>
      ))}
    </tr>
  )
}

export default function Compare() {
  const navigate = useNavigate()
  const api = useApi<WatchlistStock[]>('/watchlist')
  const [selectedCodes, setSelectedCodes] = useState<string[]>([])
  const [analyses, setAnalyses] = useState<Record<string, AnalysisData | null>>({})
  const [loadingAnalyses, setLoadingAnalyses] = useState<Record<string, boolean>>({})

  const stocks: WatchlistStock[] = useMemo(() => {
    if (!api.data || !Array.isArray(api.data)) return []
    return api.data.map(s => ({
      ...s,
      status: (s.compositeScore >= 70 ? 'active' : 'revisit') as 'active' | 'revisit' | 'removed',
    }))
  }, [api.data])

  // Fetch analysis for selected stocks
  useEffect(() => {
    if (!API_URL) return
    for (const code of selectedCodes) {
      if (analyses[code] !== undefined || loadingAnalyses[code]) continue
      setLoadingAnalyses(prev => ({ ...prev, [code]: true }))
      fetch(`${API_URL}/analysis/${code}`)
        .then(r => r.ok ? r.json() : null)
        .then(d => {
          setAnalyses(prev => ({ ...prev, [code]: d }))
          setLoadingAnalyses(prev => ({ ...prev, [code]: false }))
        })
        .catch(() => {
          setAnalyses(prev => ({ ...prev, [code]: null }))
          setLoadingAnalyses(prev => ({ ...prev, [code]: false }))
        })
    }
  }, [selectedCodes, API_URL])

  const selectedStocks: ComparisonStock[] = useMemo(() => {
    return selectedCodes.map(code => {
      const stock = stocks.find(s => s.code === code)
      const analysis = analyses[code] || undefined
      return { ...(stock || { code, name: code, industry: '', lastPrice: 0, status: 'revisit' as const, compositeScore: 0, hasAiReport: false, peRatio: null, dividendYield: null, roe: null, debtToEquity: null, marketCap: null }), analysis }
    })
  }, [selectedCodes, stocks, analyses])

  const toggleStock = (code: string) => {
    setSelectedCodes(prev => {
      if (prev.includes(code)) return prev.filter(c => c !== code)
      if (prev.length >= MAX_COMPARE) return prev
      return [...prev, code]
    })
  }

  const removeStock = (code: string) => {
    setSelectedCodes(prev => prev.filter(c => c !== code))
  }

  const formatPrice = (v: string | number) => {
    const n = typeof v === 'string' ? parseFloat(v) : v
    return isNaN(n) ? '-' : `RM ${n.toFixed(2)}`
  }

  const formatScore = (v: string | number) => {
    const n = typeof v === 'string' ? parseFloat(v) : v
    return isNaN(n) ? '-' : `${Math.round(n)}/100`
  }

  const formatNum = (v: number | null | undefined, suffix = '', decimals = 1) => {
    if (v == null || isNaN(v)) return '-'
    if (suffix === 'x') return `${v.toFixed(decimals)}x`
    if (suffix === '%') return `${v.toFixed(decimals)}%`
    return `${v.toFixed(decimals)}${suffix}`
  }

  const formatMarketCap = (v: number | null | undefined) => {
    if (v == null || isNaN(v)) return '-'
    if (v >= 1e12) return `RM ${(v / 1e12).toFixed(2)}T`
    if (v >= 1e9) return `RM ${(v / 1e9).toFixed(1)}B`
    if (v >= 1e6) return `RM ${(v / 1e6).toFixed(0)}M`
    return `RM ${v.toFixed(0)}`
  }

  // Extract score breakdown from analysis
  const getScoreBreakdown = (stock: ComparisonStock) => {
    const bd = stock.analysis?.score_breakdown
    if (!bd) return null
    return {
      dividend: typeof bd.dividend === 'number' ? bd.dividend : (bd as any).dividend_score || 0,
      growth: typeof bd.growth === 'number' ? bd.growth : (bd as any).growth_score || 0,
      quality: typeof bd.quality === 'number' ? bd.quality : (bd as any).quality_score || 0,
      risk: typeof bd.risk === 'number' ? bd.risk : (bd as any).risk_score || 0,
    }
  }

  // Get Kronos signal summary
  const getKronosSignal = (stock: ComparisonStock) => {
    const ks = stock.analysis?.kronos_signal
    if (!ks || typeof ks !== 'object') return null
    const pct = (ks as any).pred_change_pct
    if (typeof pct === 'number') {
      const sign = pct > 0 ? '+' : ''
      return `${sign}${pct.toFixed(1)}%`
    }
    return null
  }

  return (
    <div className="min-h-screen">
      <Helmet {...seo({
        title: 'Compare Stocks — Divvy Bursa Tracker',
        description: 'Side-by-side comparison of Bursa Malaysia stocks. Compare composite scores, financials, dividends, valuations, and AI analysis across 2-3 stocks at once.',
        canonical: '/compare',
      })} />
      <main className="max-w-5xl mx-auto px-4 py-6">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 flex items-center gap-2">
            <GitCompare className="w-6 h-6 text-emerald-600" />
            Compare Stocks
          </h1>
        </div>

        {/* Stock Selector */}
        <div className="mb-8">
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-3">
            Select 2–3 stocks to compare side-by-side
          </p>

          {selectedCodes.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-4">
              {selectedCodes.map(code => {
                const stock = stocks.find(s => s.code === code)
                return (
                  <span key={code} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-emerald-100 dark:bg-emerald-900 text-emerald-700 dark:text-emerald-300 text-sm font-medium">
                    {stock?.name || code}
                    <button onClick={() => removeStock(code)} className="hover:text-emerald-900 dark:hover:text-emerald-100" aria-label={`Remove ${stock?.name || code}`}>
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </span>
                )
              })}
              {selectedCodes.length < MAX_COMPARE && (
                <span className="text-sm text-gray-400 dark:text-gray-500 flex items-center">
                  <Plus className="w-3.5 h-3.5 mr-1" />
                  Select {MAX_COMPARE - selectedCodes.length} more
                </span>
              )}
            </div>
          )}

          {api.loading ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="h-10 bg-gray-100 dark:bg-gray-800 rounded-lg animate-pulse" />
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
              {stocks
                .sort((a, b) => b.compositeScore - a.compositeScore)
                .map(stock => {
                  const isSelected = selectedCodes.includes(stock.code)
                  const indColor = INDUSTRY_COLORS[stock.industry] || 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200'
                  return (
                    <button
                      key={stock.code}
                      onClick={() => toggleStock(stock.code)}
                      disabled={!isSelected && selectedCodes.length >= MAX_COMPARE}
                      className={`text-left px-3 py-2 rounded-lg border text-sm transition-all ${
                        isSelected
                          ? 'border-emerald-500 bg-emerald-50 dark:bg-emerald-950 dark:border-emerald-600 ring-2 ring-emerald-500/20'
                          : selectedCodes.length >= MAX_COMPARE
                          ? 'border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 opacity-50 cursor-not-allowed'
                          : 'border-gray-200 dark:border-gray-700 hover:border-emerald-300 dark:hover:border-emerald-700 bg-white dark:bg-gray-900'
                      }`}
                    >
                      <div className="font-medium text-gray-900 dark:text-gray-100 truncate">{stock.name}</div>
                      <div className="flex items-center justify-between mt-1">
                        <span className={`text-xs px-1.5 py-0.5 rounded ${indColor}`}>{stock.industry || '—'}</span>
                        <span className="text-xs font-semibold text-gray-500 dark:text-gray-400">{stock.compositeScore}</span>
                      </div>
                    </button>
                  )
                })}
            </div>
          )}
        </div>

        {/* Comparison Table */}
        {selectedStocks.length >= 2 ? (
          <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200 dark:border-gray-800">
                    <th className="py-3 px-4 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">Metric</th>
                    {selectedStocks.map((stock, i) => (
                      <th key={i} className="py-3 px-4 text-center">
                        <button
                          onClick={() => navigate(`/stock/${stock.code}`)}
                          className="text-sm font-semibold text-gray-900 dark:text-gray-100 hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors"
                        >
                          {stock.name}
                        </button>
                        <div className="flex items-center justify-center gap-2 mt-1">
                          <span className={`text-xs px-1.5 py-0.5 rounded ${INDUSTRY_COLORS[stock.industry] || 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200'}`}>
                            {stock.industry || '—'}
                          </span>
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                  <MetricRow
                    label="Score"
                    icon={BarChart3}
                    values={selectedStocks.map(s => formatScore(s.compositeScore))}
                    highlight
                  />
                  <MetricRow
                    label="Last Price"
                    icon={DollarSign}
                    values={selectedStocks.map(s => formatPrice(s.lastPrice))}
                  />
                  <MetricRow
                    label="Status"
                    values={selectedStocks.map(s => s.status.charAt(0).toUpperCase() + s.status.slice(1))}
                  />
                  <MetricRow
                    label="P/E Ratio"
                    values={selectedStocks.map(s => formatNum(s.peRatio, 'x', 1))}
                  />
                  <MetricRow
                    label="Div Yield"
                    values={selectedStocks.map(s => formatNum(s.dividendYield, '%', 1))}
                  />
                  <MetricRow
                    label="ROE"
                    values={selectedStocks.map(s => formatNum(s.roe, '%', 1))}
                  />
                  <MetricRow
                    label="D/E Ratio"
                    values={selectedStocks.map(s => formatNum(s.debtToEquity, '', 2))}
                  />
                  <MetricRow
                    label="Market Cap"
                    values={selectedStocks.map(s => formatMarketCap(s.marketCap))}
                  />
                </tbody>
              </table>
            </div>

            {/* Score Breakdown */}
            <div className="border-t border-gray-200 dark:border-gray-800 px-4 py-4">
              <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">Score Breakdown</h3>
              <div className="grid gap-3" style={{ gridTemplateColumns: `repeat(${selectedStocks.length}, 1fr)` }}>
                {selectedStocks.map((stock, i) => {
                  const bd = getScoreBreakdown(stock)
                  return (
                    <div key={i} className="space-y-2">
                      <div className="flex items-center justify-center mb-2">
                        <ScoreBadge score={stock.compositeScore} size="sm" />
                      </div>
                      {bd ? (
                        <>
                          {(['dividend', 'growth', 'quality', 'risk'] as const).map(pillar => (
                            <div key={pillar} className="flex items-center gap-2">
                              <span className="text-xs text-gray-500 dark:text-gray-400 w-16 capitalize">{pillar}</span>
                              <div className="flex-1 h-1.5 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                                <div
                                  className={`h-full rounded-full ${
                                    pillar === 'dividend' ? 'bg-blue-500' :
                                    pillar === 'growth' ? 'bg-purple-500' :
                                    pillar === 'quality' ? 'bg-amber-500' : 'bg-red-400'
                                  }`}
                                  style={{ width: `${Math.min((bd[pillar] / 40) * 100, 100)}%` }}
                                />
                              </div>
                              <span className="text-xs font-mono text-gray-600 dark:text-gray-400 w-6 text-right">{bd[pillar]}</span>
                            </div>
                          ))}
                        </>
                      ) : loadingAnalyses[stock.code] ? (
                        <div className="space-y-2">
                          {Array.from({ length: 4 }).map((_, j) => (
                            <div key={j} className="h-2 bg-gray-100 dark:bg-gray-800 rounded animate-pulse" />
                          ))}
                        </div>
                      ) : (
                        <p className="text-xs text-gray-400 text-center py-2">No breakdown available</p>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Kronos / AI Signals */}
            <div className="border-t border-gray-200 dark:border-gray-800 px-4 py-4">
              <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">AI Signals</h3>
              <div className="grid gap-3" style={{ gridTemplateColumns: `repeat(${selectedStocks.length}, 1fr)` }}>
                {selectedStocks.map((stock, i) => {
                  const kronos = getKronosSignal(stock)
                  return (
                    <div key={i} className="text-center">
                      {kronos ? (
                        <span className={`text-sm font-semibold ${kronos.startsWith('+') ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
                          Kronos {kronos}
                        </span>
                      ) : loadingAnalyses[stock.code] ? (
                        <div className="h-4 w-20 bg-gray-100 dark:bg-gray-800 rounded animate-pulse mx-auto" />
                      ) : (
                        <span className="text-sm text-gray-400">—</span>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Quick actions */}
            <div className="border-t border-gray-200 dark:border-gray-800 px-4 py-3 flex justify-center gap-4">
              {selectedStocks.map((stock, i) => (
                <button
                  key={i}
                  onClick={() => navigate(`/stock/${stock.code}`)}
                  className="inline-flex items-center gap-1 text-xs text-emerald-600 dark:text-emerald-400 hover:text-emerald-700 dark:hover:text-emerald-300 font-medium"
                >
                  View {stock.name.split(' ')[0]}
                  <ArrowRight className="w-3 h-3" />
                </button>
              ))}
            </div>
          </div>
        ) : selectedStocks.length === 1 ? (
          <div className="text-center py-16 bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800">
            <GitCompare className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-700 dark:text-gray-300 mb-1">Select at least 2 stocks</h3>
            <p className="text-sm text-gray-500 mb-5 max-w-sm mx-auto">
              Choose 2–3 stocks from the grid above to compare their metrics side-by-side.
            </p>
          </div>
        ) : api.data && api.data.length > 0 ? (
          <div className="text-center py-16 bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800">
            <GitCompare className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-700 dark:text-gray-300 mb-1">Select stocks to compare</h3>
            <p className="text-sm text-gray-500 max-w-sm mx-auto">
              Click on stocks from the grid above to add them to the comparison table. Compare up to 3 stocks at once.
            </p>
          </div>
        ) : null}
      </main>
    </div>
  )
}
