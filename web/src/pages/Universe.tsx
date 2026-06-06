import { useState, useMemo } from 'react'
import { Search, Beaker, Loader2, CheckCircle2, Clock } from 'lucide-react'
import { useApi } from '../hooks/useApi'

interface UniverseStock {
  stock_code: string
  name: string
  industry: string | null
  market_cap: number | null
  last_price: number | null
  pe_ratio: number | null
  dividend_yield: number | null
  has_analysis: boolean
  last_analyzed_at: string | null
  added_at: string
}

interface UniverseResponse {
  data: UniverseStock[]
  pagination: { total: number }
}

export default function Universe() {
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [submittedSearch, setSubmittedSearch] = useState('')
  const [requesting, setRequesting] = useState<Set<string>>(new Set())
  const [queued, setQueued] = useState<Set<string>>(new Set())
  const [message, setMessage] = useState('')

  const url = useMemo(() => {
    const params = new URLSearchParams({ page: String(page), limit: '50' })
    if (submittedSearch) params.set('search', submittedSearch)
    return `/universe?${params}`
  }, [page, submittedSearch])

  const api = useApi<UniverseResponse>(url)

  const stocks = api.data?.data || []
  const total = api.data?.pagination?.total || 0

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setPage(1)
    setSubmittedSearch(search)
  }

  const requestAnalysis = async (stockCode: string) => {
    const API_URL = import.meta.env.VITE_API_URL || ''
    if (!API_URL || requesting.has(stockCode) || queued.has(stockCode)) return
    setRequesting(prev => new Set(prev).add(stockCode))
    try {
      const res = await fetch(`${API_URL}/universe/request-analysis`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ stockCode }),
      })
      const json = await res.json()
      if (json.success) {
        setQueued(prev => new Set(prev).add(stockCode))
        setMessage(`Queued ${stockCode.replace('.KL','')} for deep analysis`)
        setTimeout(() => setMessage(''), 4000)
      }
    } catch (e) {
      console.error(e)
    }
    setRequesting(prev => {
      const next = new Set(prev)
      next.delete(stockCode)
      return next
    })
  }

  const formatDate = (d: string | null) => {
    if (!d) return null
    return new Date(d).toLocaleDateString('en-MY', { day: 'numeric', month: 'short', year: '2-digit' })
  }

  const totalPages = Math.ceil(total / 50)

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      <main className="max-w-5xl mx-auto px-4 py-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Bursa Universe</h1>
            <p className="text-sm text-gray-500">{total.toLocaleString()} stocks · Request deep analysis on any stock</p>
          </div>
        </div>

        {message && (
          <div role="status" aria-live="polite" className="mb-4 px-4 py-2 bg-emerald-100 dark:bg-emerald-900 text-emerald-800 dark:text-emerald-200 rounded-lg text-sm flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4" />
            {message}
          </div>
        )}

        <form onSubmit={handleSearch} role="search" aria-label="Search Bursa stocks" className="mb-4 flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <label htmlFor="universe-search" className="sr-only">Search stocks</label>
            <input
              id="universe-search"
              type="text"
              placeholder="Search by name or code..."
              aria-label="Search Bursa stocks"
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 text-sm focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
            />
          </div>
          <button
            type="submit"
            className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 transition-colors"
          >
            Search
          </button>
        </form>

        {api.loading ? (
          <div role="status" aria-live="polite" className="flex items-center justify-center py-20">
            <Loader2 className="h-6 w-6 animate-spin text-emerald-600" />
            <span className="sr-only">Loading stocks...</span>
          </div>
        ) : (
          <>
            <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900">
                      <th className="text-left px-4 py-3 font-medium text-gray-500">Code</th>
                      <th className="text-left px-4 py-3 font-medium text-gray-500">Name</th>
                      <th className="text-left px-4 py-3 font-medium text-gray-500 hidden sm:table-cell">Industry</th>
                      <th className="text-right px-4 py-3 font-medium text-gray-500 hidden md:table-cell">Price</th>
                      <th className="text-center px-4 py-3 font-medium text-gray-500">Status</th>
                      <th className="text-center px-4 py-3 font-medium text-gray-500">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stocks.map(s => (
                      <tr key={s.stock_code} className="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-850">
                        <td className="px-4 py-3 font-mono text-xs text-gray-600 dark:text-gray-400">{s.stock_code.replace('.KL', '')}</td>
                        <td className="px-4 py-3 text-gray-900 dark:text-gray-100 max-w-[200px] truncate">{s.name}</td>
                        <td className="px-4 py-3 text-gray-500 hidden sm:table-cell">{s.industry || '—'}</td>
                        <td className="px-4 py-3 text-right text-gray-700 dark:text-gray-300 hidden md:table-cell">
                          {s.last_price ? `RM ${Number(s.last_price).toFixed(2)}` : '—'}
                        </td>
                        <td className="px-4 py-3 text-center">
                          {s.has_analysis ? (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300" title={s.last_analyzed_at ? `Last analyzed: ${formatDate(s.last_analyzed_at)}` : undefined}>
                              <CheckCircle2 className="h-3 w-3" />
                              {s.last_analyzed_at ? formatDate(s.last_analyzed_at) : 'Analyzed'}
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300">
                              <Clock className="h-3 w-3" />
                              Pending
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-center">
                          <button
                            onClick={() => requestAnalysis(s.stock_code)}
                            aria-label={`Request analysis for ${s.name}`}
                            disabled={s.has_analysis || queued.has(s.stock_code) || requesting.has(s.stock_code)}
                            className={`inline-flex items-center gap-1 px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
                              s.has_analysis
                                ? 'bg-gray-100 text-gray-400 cursor-not-allowed dark:bg-gray-800'
                                : queued.has(s.stock_code)
                                ? 'bg-gray-100 text-gray-400 cursor-not-allowed dark:bg-gray-800'
                                : requesting.has(s.stock_code)
                                ? 'bg-emerald-100 text-emerald-600 dark:bg-emerald-900'
                                : 'bg-emerald-600 text-white hover:bg-emerald-700'
                            }`}
                          >
                            {requesting.has(s.stock_code) ? (
                              <Loader2 className="h-3 w-3 animate-spin" />
                            ) : (
                              <Beaker className="h-3 w-3" />
                            )}
                            {s.has_analysis ? 'Done' : queued.has(s.stock_code) ? 'Queued' : requesting.has(s.stock_code) ? 'Queueing' : 'Analyze'}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {totalPages > 1 && (
              <div className="flex items-center justify-center gap-2 mt-4">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  aria-label="Previous page"
                  className="px-3 py-1 rounded text-sm bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 disabled:opacity-50"
                >
                  Prev
                </button>
                <span className="text-sm text-gray-500" aria-live="polite">
                  Page {page} of {totalPages}
                </span>
                <button
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  aria-label="Next page"
                  className="px-3 py-1 rounded text-sm bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 disabled:opacity-50"
                >
                  Next
                </button>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  )
}
