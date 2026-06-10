import { useState, useMemo } from 'react'
import { Helmet } from 'react-helmet-async'
import { seo } from '../lib/seo'
import StockCard from '../components/StockCard'
import IndustryFilter from '../components/IndustryFilter'
import { useApi } from '../hooks/useApi'
import { TICKER_TO_SHORT } from '../data/stocks'
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
  const api = useApi<WatchlistStock[]>('/watchlist')

  const allStocks: (Stock & { _ticker: string; _shortCode: string })[] = useMemo(() => {
    if (!api.data || !Array.isArray(api.data)) return []
    return api.data.map(apiStockToStock)
  }, [api.data])

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
      <Helmet {...seo({
        title: 'Divvy — Bursa Investment Tracker',
        description: `AI-powered Bursa Malaysia investment tracker. Browse ${allStocks.length} tracked stocks with composite scores, industry filters, and live KLSE prices.`,
        canonical: 'https://d2d7b6u77b6we4.cloudfront.net/',
      })} />
      <main className="max-w-7xl mx-auto px-4 py-6">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-1">
            Bursa Investment Tracker
          </h1>
          <p className="text-sm text-gray-500">
            {allStocks.length} stocks tracked · High dividend yield & growth potential
          </p>
        </div>

        {api.loading ? (
          <div role="status" aria-live="polite" className="text-center py-20">
            <p className="text-gray-400 text-lg">Loading stocks...</p>
          </div>
        ) : allStocks.length === 0 ? (
          <div role="status" className="text-center py-20">
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
                <label htmlFor="min-score-filter" className="text-xs text-gray-500">Min Score:</label>
                <input
                  id="min-score-filter"
                  type="range"
                  min={0} max={100} value={minScore}
                  onChange={(e) => setMinScore(Number(e.target.value))}
                  className="w-24 accent-emerald-600"
                  aria-valuemin={0} aria-valuemax={100} aria-valuenow={minScore}
                  aria-label="Minimum composite score filter"
                />
                <span className="text-xs font-medium text-gray-700 dark:text-gray-300 w-8" aria-live="polite">{minScore}</span>
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
