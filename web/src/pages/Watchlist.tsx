import { useState, useMemo } from 'react'
import { Search, FolderOpen, ArrowRight, Download } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import ScoreBadge from '../components/ScoreBadge'
import { INDUSTRY_COLORS } from '../data/stocks'
import { useApi } from '../hooks/useApi'
import { downloadCsv, type CsvRow } from '../lib/export-csv'
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

type Tab = 'active' | 'revisit' | 'removed'

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

// Reverse: ticker → short code
const TICKER_TO_SHORT: Record<string, string> = {}
for (const [short, ticker] of Object.entries(TICKER_MAP)) {
  TICKER_TO_SHORT[ticker] = short
}

function apiStockToStock(s: WatchlistStock): Stock {
  const shortCode = TICKER_TO_SHORT[s.code] || s.code
  return {
    code: s.code,  // keep ticker code for navigation
    name: s.name,
    industry: s.industry,
    marketCap: 0,
    lastPrice: s.lastPrice,
    priceChange: 0,
    dividendYield: 0,
    score: { composite: s.compositeScore, dividend: 0, growth: 0, quality: 0, risk: 0 },
    financials: [],
    dividends: [],
    status: s.compositeScore >= 70 ? 'active' : 'revisit',
    addedAt: '',
    revisitAt: null,
    notes: '',
    sparkline: [],
    // Store short code for display
    _shortCode: shortCode,
    hasAiReport: s.hasAiReport,
  } as Stock & { _shortCode: string; hasAiReport: boolean }
}

type ExtendedStock = ReturnType<typeof apiStockToStock>

export default function Watchlist() {
  const [tab, setTab] = useState<Tab>('active')
  const api = useApi<WatchlistStock[]>('/watchlist')

  const dbStocks: ExtendedStock[] = useMemo(() => {
    if (!api.data || !Array.isArray(api.data)) return []
    return api.data.map(apiStockToStock)
  }, [api.data])

  // Derive status dynamically from score (≥70 = active)
  const mergedStocks = useMemo(() =>
    dbStocks.map(s => ({
      ...s,
      status: (s.score.composite >= 70 ? 'active' : 'revisit') as 'active' | 'revisit' | 'removed',
    })),
    [dbStocks]
  )

  const active = useMemo(() =>
    mergedStocks.filter((s) => s.status === 'active').sort((a, b) => b.score.composite - a.score.composite),
    [mergedStocks]
  )
  const revisit = useMemo(() =>
    mergedStocks.filter((s) => s.status === 'revisit').sort((a, b) => b.score.composite - a.score.composite),
    [mergedStocks]
  )
  const removed = useMemo(() =>
    mergedStocks.filter((s) => s.status === 'removed'),
    [mergedStocks]
  )

  const data = tab === 'active' ? active : tab === 'revisit' ? revisit : removed

  const tabClass = (t: Tab) =>
    `px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
      tab === t
        ? 'border-emerald-600 text-emerald-600 dark:text-emerald-400'
        : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
    }`

  function StockRow({ stock }: { stock: ExtendedStock }) {
    const navigate = useNavigate()
    const indColor = INDUSTRY_COLORS[stock.industry] || 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200'
    const statusColor =
      stock.status === 'active' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300' :
      stock.status === 'revisit' ? 'bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300' :
      'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400'

    const displayCode = (stock as any)._shortCode || stock.code

    return (
      <div
        className="flex items-center justify-between py-3 px-3 md:px-4 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-900 hover:shadow-sm hover:scale-[1.005] transition-all duration-150 cursor-pointer gap-2"
        onClick={() => navigate(`/stock/${stock.code}`)}
      >
        <div className="flex items-center gap-2 md:gap-3 min-w-0 flex-1">
          <ScoreBadge score={stock.score.composite} size="sm" />
          <div className="min-w-0">
            <p className="font-medium text-sm md:text-base text-gray-900 dark:text-gray-100 truncate">{stock.name}</p>
            <p className="text-xs text-gray-500 truncate">{displayCode} · {stock.industry}</p>
          </div>
        </div>
        <div className="flex items-center gap-2 md:gap-4 flex-shrink-0">
          <span className={`px-2 py-0.5 rounded-full text-[10px] md:text-xs font-medium hidden sm:inline ${indColor}`}>{stock.industry}</span>
          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusColor}`}>
            {stock.status}
          </span>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen">
      <main className="max-w-3xl mx-auto px-4 py-6">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Watchlist</h1>
          {mergedStocks.length > 0 && (
            <button
              onClick={() => {
                const rows: CsvRow[] = mergedStocks.map(s => ({
                  code: (s as any)._shortCode || s.code,
                  name: s.name,
                  industry: s.industry,
                  lastPrice: s.lastPrice,
                  dividendYield: s.dividendYield,
                  pe: s.financials?.[0]?.peRatio ?? 0,
                  score: s.score.composite,
                  status: s.status,
                  hasAiReport: (s as any).hasAiReport ?? false,
                }))
                downloadCsv(rows)
              }}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-emerald-700 bg-emerald-50 hover:bg-emerald-100 dark:text-emerald-400 dark:bg-emerald-950 dark:hover:bg-emerald-900 rounded-lg transition-colors"
              title="Export watchlist to CSV"
            >
              <Download className="w-3.5 h-3.5" />
              Export CSV
            </button>
          )}
        </div>

        <div className="flex border-b border-gray-200 dark:border-gray-800 mb-4">
          {(['active', 'revisit', 'removed'] as Tab[]).map((t) => (
            <button key={t} onClick={() => setTab(t)} className={tabClass(t)}>
              {t.charAt(0).toUpperCase() + t.slice(1)}
              <span className="ml-1.5 text-xs text-gray-400">
                ({t === 'active' ? active.length : t === 'revisit' ? revisit.length : removed.length})
              </span>
            </button>
          ))}
        </div>

        {api.loading ? (
          <div className="divide-y divide-gray-100 dark:divide-gray-800">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="flex items-center justify-between py-3 px-4">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-700 animate-pulse" />
                  <div>
                    <div className="h-4 w-28 bg-gray-200 dark:bg-gray-700 rounded animate-pulse mb-1.5" />
                    <div className="h-3 w-40 bg-gray-100 dark:bg-gray-800 rounded animate-pulse" />
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="h-5 w-20 bg-gray-200 dark:bg-gray-700 rounded-full animate-pulse" />
                  <div className="h-5 w-14 bg-gray-200 dark:bg-gray-700 rounded-full animate-pulse" />
                </div>
              </div>
            ))}
          </div>
        ) : data.length === 0 ? (
          <div className="text-center py-16">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gray-100 dark:bg-gray-800 mb-4">
              {tab === 'active' ? (
                <Search className="w-8 h-8 text-gray-400" />
              ) : tab === 'revisit' ? (
                <FolderOpen className="w-8 h-8 text-gray-400" />
              ) : (
                <FolderOpen className="w-8 h-8 text-gray-400" />
              )}
            </div>
            <h3 className="text-lg font-semibold text-gray-700 dark:text-gray-300 mb-1">
              {tab === 'active' ? 'No active stocks yet' : tab === 'revisit' ? 'Nothing to revisit' : 'No removed stocks'}
            </h3>
            <p className="text-sm text-gray-500 mb-5 max-w-sm mx-auto">
              {tab === 'active'
                ? 'Stocks scoring 70+ will appear here. Run deep analysis on stocks from the universe to get started.'
                : tab === 'revisit'
                ? 'Stocks scoring below 70 land here for later review.'
                : 'Removed stocks will show up here.'}
            </p>
            <a
              href="/universe"
              className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-700 rounded-lg transition-colors"
            >
              Browse Universe
              <ArrowRight className="w-4 h-4" />
            </a>
          </div>
        ) : (
          <div className="divide-y divide-gray-100 dark:divide-gray-800">
            {data.map((stock) => (
              <StockRow key={stock.code} stock={stock} />
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
