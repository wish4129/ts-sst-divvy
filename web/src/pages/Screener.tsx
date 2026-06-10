import { useState, useMemo } from 'react'
import { Helmet } from 'react-helmet-async'
import { Search, TrendingUp, AlertCircle, Plus, ArrowUpDown, ExternalLink } from 'lucide-react'
import { seo } from '../lib/seo'
import { useNavigate } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import ScoreBadge from '../components/ScoreBadge'

interface ScreenerCandidate {
  id: number
  stockCode: string
  stockName: string
  peRatio: number | null
  dividendYield: number | null
  roe: number | null
  compositeScore: number
  scannedAt: string
  inWatchlist: boolean
}

type SortCol = 'score' | 'pe' | 'dy' | 'roe'
type SortDir = 'asc' | 'desc'

const API_URL = import.meta.env.VITE_API_URL || ''

export default function Screener() {
  const [search, setSearch] = useState('')
  const [sortCol, setSortCol] = useState<SortCol>('score')
  const [sortDir, setSortDir] = useState<SortDir>('desc')
  const [filter, setFilter] = useState<'all' | 'new' | 'in_watchlist'>('all')
  const navigate = useNavigate()

  const api = useApi<ScreenerCandidate[]>(`/screener`)

  const candidates: ScreenerCandidate[] = useMemo(() => {
    if (!api.data || !Array.isArray(api.data)) return []
    return api.data
  }, [api.data])

  const filtered = useMemo(() => {
    let list = [...candidates]

    // Search filter
    if (search.trim()) {
      const q = search.toLowerCase()
      list = list.filter(c =>
        c.stockName.toLowerCase().includes(q) ||
        c.stockCode.toLowerCase().includes(q)
      )
    }

    // Status filter
    if (filter === 'new') list = list.filter(c => !c.inWatchlist)
    if (filter === 'in_watchlist') list = list.filter(c => c.inWatchlist)

    // Sort
    list.sort((a, b) => {
      const getVal = (c: ScreenerCandidate): number => {
        switch (sortCol) {
          case 'score': return c.compositeScore
          case 'pe': return c.peRatio ?? 9999
          case 'dy': return c.dividendYield ?? 0
          case 'roe': return c.roe ?? 0
        }
      }
      const va = getVal(a), vb = getVal(b)
      return sortDir === 'desc' ? vb - va : va - vb
    })

    return list
  }, [candidates, search, filter, sortCol, sortDir])

  const toggleSort = (col: SortCol) => {
    if (sortCol === col) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortCol(col); setSortDir('desc') }
  }

  const sortIcon = (col: SortCol) => {
    if (sortCol !== col) return <ArrowUpDown className="w-3 h-3 inline ml-1 opacity-40" />
    return sortDir === 'asc'
      ? <span className="ml-1 text-xs">▲</span>
      : <span className="ml-1 text-xs">▼</span>
  }

  const inWatchlistCount = candidates.filter(c => c.inWatchlist).length
  const newCount = candidates.filter(c => !c.inWatchlist).length

  const addToWatchlist = (stockCode: string) => {
    navigate(`/universe?add=${stockCode}`)
  }

  if (api.loading) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-8">
        <h1 className="text-2xl font-bold mb-6">Stock Screener</h1>
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-16 bg-gray-100 dark:bg-gray-800 rounded-lg animate-pulse" />
          ))}
        </div>
      </div>
    )
  }

  if (api.error) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-8 text-center">
        <AlertCircle className="w-12 h-12 mx-auto mb-4 text-red-500" />
        <h2 className="text-xl font-semibold mb-2">Failed to load screener data</h2>
        <p className="text-gray-500 mb-4">{api.error}</p>
        <button onClick={api.refetch} className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700">
          Retry
        </button>
      </div>
    )
  }

  if (candidates.length === 0 && !api.loading) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-8 text-center">
        <TrendingUp className="w-16 h-16 mx-auto mb-4 text-gray-300" />
        <h2 className="text-xl font-semibold mb-2">No Screener Candidates Yet</h2>
        <p className="text-gray-500 mb-4">
          The stock screener runs every Monday morning to find high-dividend, undervalued Bursa Malaysia stocks.
          Check back after the next scan, or browse the <a href="/universe" className="text-indigo-600 hover:underline">Bursa Universe</a>.
        </p>
      </div>
    )
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <Helmet {...seo({
        title: 'Stock Screener — Divvy Bursa Tracker',
        description: `Bursa Malaysia stock screener. ${newCount} new candidates, ${inWatchlistCount} tracked. Screen for high-dividend, undervalued KLSE stocks with AI-powered scoring.`,
        canonical: 'https://d2d7b6u77b6we4.cloudfront.net/screener',
      })} />
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold">Stock Screener</h1>
          <p className="text-sm text-gray-500 mt-1">
            {newCount} new candidates · {inWatchlistCount} already tracked
          </p>
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search stocks..."
            className="pl-9 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-sm w-48"
          />
        </div>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-2 mb-4">
        {([
          ['all', `All (${candidates.length})`],
          ['new', `New (${newCount})`],
          ['in_watchlist', `In Watchlist (${inWatchlistCount})`],
        ] as const).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setFilter(key)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              filter === key
                ? 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300'
                : 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
                <th className="text-left px-4 py-3 font-medium text-gray-600 dark:text-gray-400">Stock</th>
                <th
                  className="text-right px-4 py-3 font-medium text-gray-600 dark:text-gray-400 cursor-pointer hover:text-gray-900 dark:hover:text-gray-200"
                  onClick={() => toggleSort('score')}
                >
                  Score{sortIcon('score')}
                </th>
                <th
                  className="text-right px-4 py-3 font-medium text-gray-600 dark:text-gray-400 cursor-pointer hover:text-gray-900 dark:hover:text-gray-200"
                  onClick={() => toggleSort('pe')}
                >
                  P/E{sortIcon('pe')}
                </th>
                <th
                  className="text-right px-4 py-3 font-medium text-gray-600 dark:text-gray-400 cursor-pointer hover:text-gray-900 dark:hover:text-gray-200"
                  onClick={() => toggleSort('dy')}
                >
                  DY%{sortIcon('dy')}
                </th>
                <th
                  className="text-right px-4 py-3 font-medium text-gray-600 dark:text-gray-400 cursor-pointer hover:text-gray-900 dark:hover:text-gray-200"
                  onClick={() => toggleSort('roe')}
                >
                  ROE%{sortIcon('roe')}
                </th>
                <th className="text-center px-4 py-3 font-medium text-gray-600 dark:text-gray-400">Status</th>
                <th className="text-center px-4 py-3 font-medium text-gray-600 dark:text-gray-400">Action</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-gray-400">
                    {search ? 'No stocks match your search' : 'No candidates in this category'}
                  </td>
                </tr>
              ) : (
                filtered.map(c => (
                  <tr
                    key={c.id}
                    className="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/30 hover:border-l-2 hover:border-l-emerald-400 transition-all duration-150"
                  >
                    <td className="px-4 py-3">
                      <div className="font-medium text-gray-900 dark:text-gray-100">{c.stockName}</div>
                      <div className="text-xs text-gray-400">{c.stockCode.replace('.KL', '')}</div>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <ScoreBadge score={c.compositeScore} />
                    </td>
                    <td className="px-4 py-3 text-right text-gray-700 dark:text-gray-300 font-mono">
                      {c.peRatio != null ? c.peRatio.toFixed(1) : '—'}
                    </td>
                    <td className="px-4 py-3 text-right text-gray-700 dark:text-gray-300 font-mono">
                      {c.dividendYield != null ? c.dividendYield.toFixed(1) + '%' : '—'}
                    </td>
                    <td className="px-4 py-3 text-right text-gray-700 dark:text-gray-300 font-mono">
                      {c.roe != null ? c.roe.toFixed(1) + '%' : '—'}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {c.inWatchlist ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400">
                          In Watchlist
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
                          New
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {c.inWatchlist ? (
                        <button
                          onClick={() => navigate(`/stock/${c.stockCode}`)}
                          className="inline-flex items-center gap-1 px-2.5 py-1 text-xs rounded-lg bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                        >
                          View <ExternalLink className="w-3 h-3" />
                        </button>
                      ) : (
                        <button
                          onClick={() => addToWatchlist(c.stockCode)}
                          className="inline-flex items-center gap-1 px-2.5 py-1 text-xs rounded-lg bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300 hover:bg-indigo-200 dark:hover:bg-indigo-900/60 transition-colors"
                        >
                          <Plus className="w-3 h-3" /> Add
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="mt-4 text-xs text-gray-400 text-center">
        Screener data refreshes weekly. Deduplication runs on every scan — stocks already in watchlist are flagged.
      </div>
    </div>
  )
}
