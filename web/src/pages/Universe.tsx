import { useState, useEffect, useMemo, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'

const API_URL = import.meta.env.VITE_API_URL || ''

interface UniverseStock {
  code: string
  name: string
  market: string
  sector: string | null
  inWatchlist: boolean
  createdAt: string
}

interface Pagination {
  page: number
  limit: number
  total: number
  totalPages: number
}

const MARKET_COLORS: Record<string, string> = {
  'Main Market': 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  'ACE Market': 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
  'LEAP Market': 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200',
  'Unknown': 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400',
}

export default function Universe() {
  const navigate = useNavigate()
  const [stocks, setStocks] = useState<UniverseStock[]>([])
  const [pagination, setPagination] = useState<Pagination>({ page: 1, limit: 50, total: 0, totalPages: 0 })
  const [search, setSearch] = useState('')
  const [marketFilter, setMarketFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const [addingCode, setAddingCode] = useState<string | null>(null)

  const fetchStocks = useCallback(async (page: number, searchTerm: string, market: string) => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ page: String(page), limit: '50' })
      if (searchTerm) params.set('search', searchTerm)
      if (market) params.set('market', market)

      const res = await fetch(`${API_URL}/universe?${params}`)
      const data = await res.json()
      setStocks(data.data || [])
      setPagination(data.pagination || { page: 1, limit: 50, total: 0, totalPages: 0 })
    } catch (e) {
      console.error('Failed to fetch universe:', e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchStocks(1, search, marketFilter)
  }, [fetchStocks, search, marketFilter])

  const addToWatchlist = async (code: string) => {
    setAddingCode(code)
    try {
      const res = await fetch(`${API_URL}/universe/add`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ code }),
      })
      const data = await res.json()
      if (data.success) {
        // Update local state
        setStocks(prev => prev.map(s => s.code === code ? { ...s, inWatchlist: true } : s))
      }
    } catch (e) {
      console.error('Failed to add to watchlist:', e)
    } finally {
      setAddingCode(null)
    }
  }

  const markets = useMemo(() => {
    const m = new Set<string>()
    stocks.forEach(s => m.add(s.market))
    return Array.from(m).sort()
  }, [stocks])

  const totalInWatchlist = useMemo(() => stocks.filter(s => s.inWatchlist).length, [stocks])

  return (
    <div className="max-w-6xl mx-auto px-4 py-6 space-y-4">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Bursa Malaysia Universe</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          {pagination.total.toLocaleString()} listed companies · {totalInWatchlist} in watchlist
        </p>
      </div>

      {/* Search & Filter */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="flex-1 relative">
          <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            placeholder="Search by name or code..."
            value={search}
            onChange={e => { setSearch(e.target.value); fetchStocks(1, e.target.value, marketFilter) }}
            className="w-full pl-10 pr-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 text-sm focus:ring-2 focus:ring-emerald-500 focus:border-transparent outline-none"
          />
        </div>
        <select
          value={marketFilter}
          onChange={e => { setMarketFilter(e.target.value); fetchStocks(1, search, e.target.value) }}
          className="px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 text-sm focus:ring-2 focus:ring-emerald-500 outline-none"
        >
          <option value="">All Markets</option>
          <option value="Main Market">Main Market</option>
          <option value="ACE Market">ACE Market</option>
          <option value="LEAP Market">LEAP Market</option>
        </select>
      </div>

      {/* Table */}
      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600" />
          </div>
        ) : stocks.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-gray-400">
            <svg className="w-12 h-12 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="text-sm">No companies found</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/50">
                  <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-gray-400 w-24">Code</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-gray-400">Company Name</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-gray-400 w-32">Market</th>
                  <th className="text-center px-4 py-3 font-medium text-gray-500 dark:text-gray-400 w-28">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50 dark:divide-gray-800">
                {stocks.map(stock => (
                  <tr
                    key={stock.code}
                    className="hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
                  >
                    <td className="px-4 py-3 font-mono text-xs text-gray-500 dark:text-gray-400">
                      {stock.code}
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => navigate(`/stock/${stock.code}`)}
                        className="text-left font-medium text-gray-900 dark:text-white hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors truncate max-w-md block"
                      >
                        {stock.name}
                      </button>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${MARKET_COLORS[stock.market] || MARKET_COLORS['Unknown']}`}>
                        {stock.market}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      {stock.inWatchlist ? (
                        <span className="inline-flex items-center gap-1 text-xs text-emerald-600 dark:text-emerald-400 font-medium">
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                          </svg>
                          In watchlist
                        </span>
                      ) : (
                        <button
                          onClick={() => addToWatchlist(stock.code)}
                          disabled={addingCode === stock.code}
                          className="inline-flex items-center gap-1 px-3 py-1.5 bg-emerald-50 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300 hover:bg-emerald-100 dark:hover:bg-emerald-900/50 rounded-lg text-xs font-medium transition-colors disabled:opacity-50"
                        >
                          {addingCode === stock.code ? (
                            <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-emerald-600" />
                          ) : (
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                            </svg>
                          )}
                          Add
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {pagination.totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/50">
            <span className="text-xs text-gray-500">
              Page {pagination.page} of {pagination.totalPages} · {pagination.total} total
            </span>
            <div className="flex gap-1">
              <button
                onClick={() => fetchStocks(pagination.page - 1, search, marketFilter)}
                disabled={pagination.page <= 1}
                className="px-3 py-1.5 text-xs rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-30 transition-colors"
              >
                Prev
              </button>
              <button
                onClick={() => fetchStocks(pagination.page + 1, search, marketFilter)}
                disabled={pagination.page >= pagination.totalPages}
                className="px-3 py-1.5 text-xs rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-30 transition-colors"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
