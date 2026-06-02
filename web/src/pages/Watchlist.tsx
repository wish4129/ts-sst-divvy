import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import ScoreBadge from '../components/ScoreBadge'
import { stocks, INDUSTRY_COLORS } from '../data/stocks'
import type { Stock } from '../data/stocks'

type Tab = 'active' | 'revisit' | 'removed'

export default function Watchlist() {
  const [tab, setTab] = useState<Tab>('active')

  const active = useMemo(() =>
    stocks.filter((s) => s.status === 'active').sort((a, b) => b.score.composite - a.score.composite),
    []
  )
  const revisit = useMemo(() =>
    stocks.filter((s) => s.status === 'revisit').sort((a, b) => b.score.composite - a.score.composite),
    []
  )
  const removed = useMemo(() =>
    stocks.filter((s) => s.status === 'removed'),
    []
  )

  const data = tab === 'active' ? active : tab === 'revisit' ? revisit : removed

  const tabClass = (t: Tab) =>
    `px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
      tab === t
        ? 'border-emerald-600 text-emerald-600 dark:text-emerald-400'
        : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
    }`

  function daysUntil(date: string | null): string {
    if (!date) return '-'
    const d = new Date(date)
    const now = new Date()
    const diff = Math.ceil((d.getTime() - now.getTime()) / (1000 * 60 * 60 * 24))
    return diff <= 0 ? 'Due' : `${diff}d`
  }

  function StockRow({ stock }: { stock: Stock }) {
    const navigate = useNavigate()
    const indColor = INDUSTRY_COLORS[stock.industry] || 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200'
    const statusColor =
      stock.status === 'active' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300' :
      stock.status === 'revisit' ? 'bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300' :
      'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400'

    const tickerMap: Record<string, string> = {
      'MAYBANK': '1155.KL', 'YTLPOWR': '6742.KL', 'AXREIT': '5106.KL',
      'INSAS': '3379.KL', 'LIIHEN': '7089.KL', 'SCIENTEX': '4731.KL',
      'GENETEC': '0104.KL', 'KLK': '2445.KL', 'INARI': '0166.KL',
      'SIME': '4197.KL', 'MAGNI': '7087.KL', 'MBMR': '5983.KL',
      'AME': '5293.KL', 'DELEUM': '5132.KL', 'WASCO': '5142.KL',
      'KIPREIT': '5280.KL', 'INTA': 'INTA.KL',
      'RHB': '1066.KL', 'PADINI': '7052.KL',
    }

    return (
      <div
        className="flex items-center justify-between py-3 px-4 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-900 transition-colors cursor-pointer"
        onClick={() => navigate(`/stock/${tickerMap[stock.code] || stock.code}`)}
      >
        <div className="flex items-center gap-3 min-w-0">
          <ScoreBadge score={stock.score.composite} size="sm" />
          <div className="min-w-0">
            <p className="font-medium text-gray-900 dark:text-gray-100 truncate">{stock.name}</p>
            <p className="text-xs text-gray-500">{stock.code} · {stock.industry}</p>
          </div>
        </div>
        <div className="flex items-center gap-4 flex-shrink-0">
          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${indColor}`}>{stock.industry}</span>
          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusColor}`}>
            {stock.status === 'revisit' && stock.revisitAt ? daysUntil(stock.revisitAt) : stock.status}
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

        {data.length === 0 ? (
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
