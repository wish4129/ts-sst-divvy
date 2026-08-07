import { useState, useEffect } from 'react'
import { Helmet } from 'react-helmet-async'
import { Search, TrendingUp, MousePointerClick, Clock, Hash } from 'lucide-react'
import { seo } from '../lib/seo'

interface TopTerm {
  query: string
  count: number
  avgResultCount: number
  lastSearchedAt: string
}

interface AnalyticsData {
  periodDays: number
  totalSearches: number
  topTerms: TopTerm[]
}

export default function Analytics() {
  const [data, setData] = useState<AnalyticsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [days, setDays] = useState(30)

  useEffect(() => {
    const API_URL = import.meta.env.VITE_API_URL || ''
    if (!API_URL) {
      setError('API_URL not configured')
      setLoading(false)
      return
    }
    setLoading(true)
    fetch(`${API_URL}/analytics/top-searches?days=${days}&limit=20`)
      .then(r => r.json())
      .then((d: AnalyticsData) => {
        setData(d)
        setError(null)
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [days])

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      <Helmet {...seo({
        title: 'Search Analytics — Divvy Bursa Tracker',
        description: 'Search trajectory analytics for the Bursa Universe. Track what users search for.',
        canonical: '/analytics',
        noindex: true,
      })} />
      <main className="max-w-4xl mx-auto px-4 py-6">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 flex items-center gap-2">
            <TrendingUp className="h-6 w-6 text-emerald-600" />
            Search Analytics
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Track what users search for in the Bursa Universe to prioritize data enrichment.
          </p>
        </div>

        <div className="flex items-center gap-2 mb-6">
          {[7, 14, 30, 90].map(n => (
            <button
              key={n}
              onClick={() => setDays(n)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                days === n
                  ? 'bg-emerald-600 text-white'
                  : 'bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800'
              }`}
            >
              {n}d
            </button>
          ))}
        </div>

        {loading && (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600" />
          </div>
        )}

        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 text-sm text-red-700 dark:text-red-400">
            {error}
          </div>
        )}

        {data && !loading && (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
              <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-4">
                <div className="flex items-center gap-2 text-gray-500 text-xs font-medium mb-1">
                  <Search className="h-3.5 w-3.5" />
                  Total Searches
                </div>
                <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                  {data.totalSearches.toLocaleString()}
                </div>
                <div className="text-xs text-gray-400 mt-1">past {days} days</div>
              </div>
              <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-4">
                <div className="flex items-center gap-2 text-gray-500 text-xs font-medium mb-1">
                  <Hash className="h-3.5 w-3.5" />
                  Unique Terms
                </div>
                <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                  {data.topTerms.length}
                </div>
                <div className="text-xs text-gray-400 mt-1">top terms shown</div>
              </div>
              <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-4">
                <div className="flex items-center gap-2 text-gray-500 text-xs font-medium mb-1">
                  <MousePointerClick className="h-3.5 w-3.5" />
                  Avg Results/Term
                </div>
                <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                  {data.topTerms.length > 0
                    ? (data.topTerms.reduce((a, t) => a + t.avgResultCount, 0) / data.topTerms.length).toFixed(1)
                    : '—'}
                </div>
                <div className="text-xs text-gray-400 mt-1">across top terms</div>
              </div>
            </div>

            {data.topTerms.length > 0 ? (
              <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900">
                      <th className="text-left px-4 py-3 font-medium text-gray-500">#</th>
                      <th className="text-left px-4 py-3 font-medium text-gray-500">Search Term</th>
                      <th className="text-right px-4 py-3 font-medium text-gray-500">Searches</th>
                      <th className="text-right px-4 py-3 font-medium text-gray-500 hidden sm:table-cell">Avg Results</th>
                      <th className="text-right px-4 py-3 font-medium text-gray-500 hidden sm:table-cell">
                        <div className="flex items-center justify-end gap-1">
                          <Clock className="h-3 w-3" />
                          Last
                        </div>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.topTerms.map((term, i) => (
                      <tr key={term.query} className="border-b border-gray-100 dark:border-gray-800">
                        <td className="px-4 py-3 text-gray-400 text-xs">{i + 1}</td>
                        <td className="px-4 py-3 font-medium text-gray-900 dark:text-gray-100">{term.query}</td>
                        <td className="px-4 py-3 text-right font-mono text-sm text-gray-900 dark:text-gray-100">{term.count}</td>
                        <td className="px-4 py-3 text-right font-mono text-sm text-gray-500 hidden sm:table-cell">{term.avgResultCount}</td>
                        <td className="px-4 py-3 text-right text-xs text-gray-400 hidden sm:table-cell">
                          {new Date(term.lastSearchedAt).toLocaleDateString('en-MY', {
                            day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'
                          })}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-8 text-center">
                <Search className="h-8 w-8 mx-auto text-gray-300 dark:text-gray-600 mb-3" />
                <p className="text-gray-500 dark:text-gray-400 text-sm">No search data yet</p>
                <p className="text-gray-400 dark:text-gray-500 text-xs mt-1">
                  Searches will appear here once users start exploring the Bursa Universe.
                </p>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  )
}
