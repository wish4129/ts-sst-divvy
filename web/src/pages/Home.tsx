import { useState, useMemo, useEffect } from 'react'
import StockCard from '../components/StockCard'
import IndustryFilter from '../components/IndustryFilter'
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

// Ticker → short code map for display (same as Watchlist)
const TICKER_TO_SHORT: Record<string, string> = {
  '1155.KL': 'MAYBANK', '6742.KL': 'YTLPOWR', '5106.KL': 'AXREIT',
  '3379.KL': 'INSAS', '7089.KL': 'LIIHEN', '4731.KL': 'SCIENTEX',
  '0104.KL': 'GENETEC', '2445.KL': 'KLK', '0166.KL': 'INARI',
  '4197.KL': 'SIME', '7087.KL': 'MAGNI', '5983.KL': 'MBMR',
  '5293.KL': 'AME', '5132.KL': 'DELEUM', '5142.KL': 'WASCO',
  '5280.KL': 'KIPREIT', 'INTA.KL': 'INTA',
  '1066.KL': 'RHB', '7052.KL': 'PADINI',
  '5398.KL': 'GAMUDA', '5236.KL': 'MATRIX',
  '1295.KL': 'PBBANK', '5031.KL': 'TIME', '0099.KL': 'SCICOM',
  '5250.KL': 'SEM',
}

function apiStockToStock(s: WatchlistStock): Stock & { _ticker: string; _shortCode: string } {
  const shortCode = TICKER_TO_SHORT[s.code] || s.code
  return {
    code: s.code,  // ticker code for API/navigation (e.g., 1155.KL)
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
    _ticker: s.code,
    _shortCode: shortCode,
  } as any
}

export default function Home() {
  const [selectedIndustry, setSelectedIndustry] = useState('')
  const [minScore, setMinScore] = useState(0)
  const [allStocks, setAllStocks] = useState<Stock[]>([])
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
          setAllStocks(data.map(apiStockToStock))
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const industries = useMemo(() =>
    [...new Set(allStocks.map((s) => s.industry))].sort(),
    [allStocks]
  )

  const filtered = useMemo(() =>
    allStocks
      .filter((s) => !selectedIndustry || s.industry === selectedIndustry)
      .filter((s) => s.score.composite >= minScore)
      .sort((a, b) => b.score.composite - a.score.composite),
    [allStocks, selectedIndustry, minScore]
  )

  return (
    <div className="min-h-screen">
      <main className="max-w-7xl mx-auto px-4 py-6">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-1">
            Bursa Investment Tracker
          </h1>
          <p className="text-sm text-gray-500">
            {allStocks.length} stocks tracked · High dividend yield & growth potential
          </p>
        </div>

        {loading ? (
          <div className="text-center py-20">
            <p className="text-gray-400 text-lg">Loading stocks...</p>
          </div>
        ) : allStocks.length === 0 ? (
          <div className="text-center py-20">
            <p className="text-gray-400 text-lg">No stocks yet.</p>
            <p className="text-gray-500 text-sm mt-1">Pipeline runs Monday 9am to discover new stocks.</p>
          </div>
        ) : (
          <>
            <div className="flex flex-col sm:flex-row gap-4 mb-6">
              <IndustryFilter
                industries={industries}
                selected={selectedIndustry}
                onChange={setSelectedIndustry}
              />
              <div className="flex items-center gap-2 flex-shrink-0">
                <span className="text-xs text-gray-500">Min Score:</span>
                <input
                  type="range"
                  min={0} max={100} value={minScore}
                  onChange={(e) => setMinScore(Number(e.target.value))}
                  className="w-24 accent-emerald-600"
                />
                <span className="text-xs font-medium text-gray-700 dark:text-gray-300 w-8">{minScore}</span>
              </div>
            </div>

            {filtered.length === 0 ? (
              <p className="text-gray-400 text-center py-10">No stocks match your filters.</p>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {filtered.map((stock, i) => (
                  <StockCard key={stock.code} stock={stock} rank={i + 1} />
                ))}
              </div>
            )}
          </>
        )}
      </main>
    </div>
  )
}
