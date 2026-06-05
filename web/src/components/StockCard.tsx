import { Link } from 'react-router-dom'
import ScoreBadge from './ScoreBadge'
import SparklineChart from './SparklineChart'
import type { Stock } from '../data/stocks'
import { INDUSTRY_COLORS } from '../data/stocks'

interface StockCardProps {
  stock: Stock & { _ticker?: string; _shortCode?: string }
  rank: number
}

export default function StockCard({ stock, rank }: StockCardProps) {
  const indColor = INDUSTRY_COLORS[stock.industry] || 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200'
  const changeColor = stock.priceChange >= 0 ? 'text-emerald-600' : 'text-red-500'
  const changeIcon = stock.priceChange >= 0 ? '▲' : '▼'

  // Use ticker code for navigation (API expects ticker), display short code
  const ticker = (stock as any)._ticker || stock.code
  const displayCode = (stock as any)._shortCode || stock.code

  return (
    <Link
      to={`/stock/${ticker}`}
      aria-label={`${stock.name} — RM ${stock.lastPrice.toFixed(2)}, Score ${stock.score.composite}`}
      className="block p-4 rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 hover:border-emerald-300 dark:hover:border-emerald-700 transition-colors"
    >
      <div className="flex items-start justify-between mb-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-gray-400">#{rank}</span>
            <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${indColor}`}>
              {stock.industry}
            </span>
          </div>
          <h3 className="font-semibold text-gray-900 dark:text-gray-100 mt-1 truncate">{stock.name}</h3>
          <p className="text-xs text-gray-500">{displayCode}</p>
        </div>
        <ScoreBadge score={stock.score.composite} size="sm" />
      </div>

      <div className="flex items-center justify-between mb-3">
        <div>
          <span className="text-lg font-bold text-gray-900 dark:text-gray-100">RM {stock.lastPrice.toFixed(2)}</span>
          <span className={`ml-2 text-xs font-medium ${changeColor}`}>
            {changeIcon} {Math.abs(stock.priceChange).toFixed(2)}%
          </span>
        </div>
        <SparklineChart data={stock.sparkline} width={80} height={28} />
      </div>

      <div className="flex items-center gap-4 text-xs text-gray-500">
        <span>DY <strong className="text-gray-700 dark:text-gray-300">{stock.dividendYield}%</strong></span>
        <span>MCap <strong className="text-gray-700 dark:text-gray-300">RM {stock.marketCap}B</strong></span>
      </div>
    </Link>
  )
}
