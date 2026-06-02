import { useParams, useSearchParams, Link } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { ArrowLeft, Brain, TrendingUp } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import ScoreBadge from '../components/ScoreBadge'
import SparklineChart from '../components/SparklineChart'
import { stocks, INDUSTRY_COLORS } from '../data/stocks'

const API_URL = import.meta.env.VITE_API_URL || ''

interface PersonaAnalysis {
  persona: string
  decision_rationale: string
  score_composite: number
  score_breakdown: Record<string, { value: number | null; raw: number; weighted: number }>
  kronos_signal: any
}

export default function StockDetail() {
  const { code } = useParams<{ code: string }>()
  const [searchParams] = useSearchParams()
  const persona = searchParams.get('persona')
  const [analysis, setAnalysis] = useState<PersonaAnalysis | null>(null)

  const stock = stocks.find((s) => s.code === code?.toUpperCase())

  useEffect(() => {
    if (persona && API_URL) {
      fetch(`${API_URL}/analysis/${code}?persona=${persona}`)
        .then(r => r.json())
        .then(d => { if (d) setAnalysis(d) })
        .catch(() => {})
    }
  }, [code, persona])

  if (!stock) {
    return (
      <div className="min-h-screen">
        <main className="max-w-3xl mx-auto px-4 py-20 text-center">
          <h1 className="text-2xl font-bold text-gray-400 mb-2">Stock not found</h1>
          <Link to="/" className="text-emerald-600 hover:text-emerald-700">Back to Dashboard</Link>
        </main>
      </div>
    )
  }

  const indColor = INDUSTRY_COLORS[stock.industry] || 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200'
  const changeColor = stock.priceChange >= 0 ? 'text-emerald-600' : 'text-red-500'
  const changeIcon = stock.priceChange >= 0 ? '▲' : '▼'
  const divData = stock.dividends.map((d) => ({ date: d.exDate.slice(0, 7), amount: d.amount, yield: d.yield }))

  return (
    <div className="min-h-screen">
      <main className="max-w-4xl mx-auto px-4 py-6">
        <Link to="/battle" className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 mb-4">
          <ArrowLeft className="w-4 h-4" /> Back to Battle
        </Link>

        {/* Persona Analysis Banner */}
        {analysis && (
          <div className="mb-6 p-5 rounded-xl border-2 border-emerald-500/30 bg-emerald-50/50 dark:bg-emerald-950/20 dark:border-emerald-500/20">
            <div className="flex items-center gap-2 mb-3">
              <Brain className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
              <h2 className="font-bold text-emerald-800 dark:text-emerald-300 capitalize">{persona}'s Analysis</h2>
              <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-900 text-emerald-700 dark:text-emerald-300">
                Score {analysis.score_composite}/100
              </span>
            </div>
            <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">{analysis.decision_rationale}</p>
            
            {/* Factor breakdown */}
            {analysis.score_breakdown && (
              <div className="mt-3 grid grid-cols-2 gap-2">
                {Object.entries(analysis.score_breakdown).map(([factor, b]: [string, any]) => (
                  <div key={factor} className="flex items-center justify-between text-xs">
                    <span className="text-gray-500 capitalize">{factor.replace(/_/g, ' ')}</span>
                    <span className="font-mono text-gray-700 dark:text-gray-300">
                      {b.weighted?.toFixed(1) || '—'}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        <div className="flex flex-wrap items-start justify-between gap-4 mb-6">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">{stock.name}</h1>
              <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${indColor}`}>{stock.industry}</span>
            </div>
            <p className="text-sm text-gray-500">{stock.code} · MCap RM {stock.marketCap}B</p>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-right">
              <span className="text-3xl font-bold text-gray-900 dark:text-gray-100">RM {stock.lastPrice.toFixed(2)}</span>
              <span className={`ml-2 text-sm font-medium ${changeColor}`}>{changeIcon} {Math.abs(stock.priceChange).toFixed(2)}%</span>
            </div>
            <ScoreBadge score={stock.score.composite} size="lg" />
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
          <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-800">
            <h2 className="font-semibold text-sm text-gray-700 dark:text-gray-300 mb-3">Score Breakdown</h2>
            {[
              { label: 'Dividend', value: stock.score.dividend, max: 40, color: 'bg-emerald-500' },
              { label: 'Growth', value: stock.score.growth, max: 30, color: 'bg-blue-500' },
              { label: 'Quality', value: stock.score.quality, max: 20, color: 'bg-violet-500' },
              { label: 'Risk', value: stock.score.risk, max: 10, color: 'bg-amber-500' },
            ].map((factor) => (
              <div key={factor.label} className="flex items-center gap-3 mb-2">
                <span className="text-xs text-gray-500 w-16">{factor.label}</span>
                <div className="flex-1 h-2 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${factor.color} rounded-full transition-all`}
                    style={{ width: `${(factor.value / factor.max) * 100}%` }}
                  />
                </div>
                <span className="text-xs font-medium text-gray-600 dark:text-gray-400 w-8 text-right">
                  {factor.value}/{factor.max}
                </span>
              </div>
            ))}
          </div>

          <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-800">
            <h2 className="font-semibold text-sm text-gray-700 dark:text-gray-300 mb-3">30-Day Price Trend</h2>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-gray-500">
                RM {Math.min(...stock.sparkline).toFixed(2)} – RM {Math.max(...stock.sparkline).toFixed(2)}
              </span>
              <span className="text-xs text-gray-500">DY {stock.dividendYield}%</span>
            </div>
            <SparklineChart data={stock.sparkline} width={300} height={60} />
          </div>
        </div>

        <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-800 mb-6">
          <h2 className="font-semibold text-sm text-gray-700 dark:text-gray-300 mb-3">Quarterly Financials</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-gray-500 border-b border-gray-200 dark:border-gray-700">
                  <th className="text-left py-2 pr-4">Quarter</th>
                  <th className="text-right py-2 px-2">Revenue</th>
                  <th className="text-right py-2 px-2">Net Income</th>
                  <th className="text-right py-2 px-2">FCF</th>
                  <th className="text-right py-2 px-2">P/E</th>
                  <th className="text-right py-2 px-2">ROE</th>
                  <th className="text-right py-2 px-2">D/E</th>
                  <th className="text-right py-2 px-2">Rev Growth</th>
                </tr>
              </thead>
              <tbody>
                {stock.financials.map((f) => (
                  <tr key={f.quarter} className="border-b border-gray-100 dark:border-gray-800">
                    <td className="py-2 pr-4 font-medium text-gray-700 dark:text-gray-300">{f.quarter}</td>
                    <td className="text-right py-2 px-2">{f.revenue.toLocaleString()}</td>
                    <td className="text-right py-2 px-2">{f.netIncome.toLocaleString()}</td>
                    <td className="text-right py-2 px-2">{f.freeCashFlow.toLocaleString()}</td>
                    <td className="text-right py-2 px-2">{f.peRatio.toFixed(1)}</td>
                    <td className="text-right py-2 px-2">{f.roe.toFixed(1)}%</td>
                    <td className="text-right py-2 px-2">{f.debtToEquity.toFixed(1)}</td>
                    <td className={`text-right py-2 px-2 ${f.revenueGrowthYoY >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                      {f.revenueGrowthYoY >= 0 ? '+' : ''}{f.revenueGrowthYoY.toFixed(1)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-800 mb-6">
          <h2 className="font-semibold text-sm text-gray-700 dark:text-gray-300 mb-3">Dividend History</h2>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={divData}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-gray-200 dark:stroke-gray-700" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} className="text-gray-500" />
              <YAxis tick={{ fontSize: 11 }} className="text-gray-500" />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'var(--tooltip-bg, #fff)',
                  border: '1px solid #e5e7eb',
                  borderRadius: '8px',
                  fontSize: '12px',
                }}
              />
              <Bar dataKey="amount" fill="#059669" radius={[4, 4, 0, 0]} name="DPS (RM)" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </main>
    </div>
  )
}
