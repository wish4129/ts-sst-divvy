import { useState, useMemo } from 'react'
import Header from '../components/Header'
import StockCard from '../components/StockCard'
import IndustryFilter from '../components/IndustryFilter'
import { stocks } from '../data/stocks'

export default function Home() {
  const [selectedIndustry, setSelectedIndustry] = useState('')
  const [minScore, setMinScore] = useState(0)

  const industries = useMemo(() =>
    [...new Set(stocks.map((s) => s.industry))].sort(),
    []
  )

  const filtered = useMemo(() =>
    stocks
      .filter((s) => !selectedIndustry || s.industry === selectedIndustry)
      .filter((s) => s.score.composite >= minScore)
      .sort((a, b) => b.score.composite - a.score.composite),
    [selectedIndustry, minScore]
  )

  return (
    <div className="min-h-screen">
      <Header />
      <main className="max-w-7xl mx-auto px-4 py-6">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-1">
            Bursa Investment Tracker
          </h1>
          <p className="text-sm text-gray-500">
            {stocks.length} stocks tracked · High dividend yield & growth potential
          </p>
        </div>

        {stocks.length === 0 ? (
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
