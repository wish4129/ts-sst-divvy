import { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import ScoreBadge from '../components/ScoreBadge'
import { INDUSTRY_COLORS } from '../data/stocks'
import type { Stock } from '../data/stocks'

const API_URL = import.meta.env.VITE_API_URL || ''

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
  } as Stock & { _shortCode: string }
}

type ExtendedStock = ReturnType<typeof apiStockToStock>

export default function Watchlist() {
  const [tab, setTab] = useState<Tab>('active')
  const [dbStocks, setDbStocks] = useState<ExtendedStock[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!API_URL) {
      setLoading(false)
      return
    }
    fetch(`${API_URL}/watchlist`)
      .then(r => r.json())
      .then((data: WatchlistStock[]) => {
        if (Array.isArray(data)) {
          const stocks = data.map(apiStockToStock)
          setDbStocks(stocks)
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

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
        className="flex items-center justify-between py-3 px-4 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-900 transition-colors cursor-pointer"
        onClick={() => navigate(`/stock/${stock.code}`)}
      >
        <div className="flex items-center gap-3 min-w-0">
          <ScoreBadge score={stock.score.composite} size="sm" />
          <div className="min-w-0">
            <p className="font-medium text-gray-900 dark:text-gray-100 truncate">{stock.name}</p>
            <p className="text-xs text-gray-500">{displayCode} · {stock.industry}</p>
          </div>
        </div>
        <div className="flex items-center gap-4 flex-shrink-0">
          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${indColor}`}>{stock.industry}</span>
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
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-6">Watchlist</h1>

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

        {loading ? (
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
          <p className="text-gray-400 text-center py-10">No stocks in this list.</p>
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
