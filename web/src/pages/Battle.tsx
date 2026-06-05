import { useState, useEffect } from 'react'
import { Trophy, TrendingUp, TrendingDown, Shield, Zap, Scale, RefreshCw, ArrowUpDown, ArrowUp, ArrowDown, ArrowRight } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'

const API_URL = import.meta.env.VITE_API_URL || ''

interface StockHolding {
  code: string
  shares: number
  cost: number
  price: number
  invested: number
  current: number
  pnl: number
  pnl_pct: number
  weight: number
}

interface PersonaSnapshot {
  total: number
  invested: number
  cash: number
  pnl: number
  pnl_pct: number
  holdings: Record<string, StockHolding>
  trades_this_run: number
}

interface RunRecord {
  timestamp: string
  personas: Record<string, PersonaSnapshot>
}

interface BattleData {
  runs: RunRecord[]
  personas: Record<string, { cash: number; holdings: Record<string, { shares: number; cost: number }> }>
  trades: any[]
}

interface PersonaDef {
  name: string
  god: string
  style: string
  strategy: string
}

const PERSONAS: Record<string, PersonaDef> = {
  ares: { name: 'Ares', god: 'God of War', style: 'Aggressive', strategy: 'Momentum + deep value. Cut -12%, no TP. 60%+ turnover.' },
  demeter: { name: 'Demeter', god: 'Harvest Goddess', style: 'Conservative', strategy: 'Dividend compound. Hold through dips. 10% cash FD.' },
  athena: { name: 'Athena', god: 'Goddess of Wisdom', style: 'Hybrid', strategy: 'GARP. Sell 50% @ +25%, buy dip @ -10%. Rotate.' },
}

const COLORS: Record<string, string> = { ares: '#ef4444', demeter: '#22c55e', athena: '#8b5cf6' }
const ICONS: Record<string, React.ComponentType<{ className?: string }>> = { ares: Zap, demeter: Shield, athena: Scale }

function formatRM(n: number) { return `RM ${n.toLocaleString('en-MY', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` }
function pctStr(n: number) { return `${n >= 0 ? '+' : ''}${n.toFixed(2)}%` }

export default function Battle() {
  const [data, setData] = useState<BattleData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [sortCol, setSortCol] = useState<string>('weight')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')

  useEffect(() => {
    const fetchBattle = async () => {
      try {
        const url = API_URL ? `${API_URL}/battle` : '/battle'
        const res = await fetch(url)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        setData(await res.json())
      } catch (e: any) {
        setError(e?.message || 'Failed to load battle data')
      } finally {
        setLoading(false)
      }
    }
    fetchBattle()
  }, [])

  const toggleSort = (col: string) => {
    if (sortCol === col) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    } else {
      setSortCol(col)
      setSortDir('desc')
    }
  }

  const sortIcon = (col: string) => {
    if (sortCol !== col) return <ArrowUpDown className="w-3 h-3 inline ml-1 opacity-40" />
    return sortDir === 'asc'
      ? <ArrowUp className="w-3 h-3 inline ml-1" />
      : <ArrowDown className="w-3 h-3 inline ml-1" />
  }

  // Sort holdings helper
  const sortHoldings = (holdings: Record<string, StockHolding>) => {
    const entries = Object.entries(holdings)
    entries.sort((a, b) => {
      const va = a[1][sortCol as keyof StockHolding] as number
      const vb = b[1][sortCol as keyof StockHolding] as number
      return sortDir === 'asc' ? va - vb : vb - va
    })
    return entries
  }

  if (loading) return <Loading />
  if (error && !data) return <ErrorMsg msg={error} />
  if (!data || !data.runs.length) return <Empty />

  const latest = data.runs[data.runs.length - 1]
  const chartData = data.runs.map(r => ({
    time: new Date(r.timestamp).toLocaleTimeString('en-MY', { hour: '2-digit', minute: '2-digit', hour12: false }),
    ...Object.fromEntries(Object.entries(r.personas).map(([k, v]) => [k, v.total])),
  }))

  const ranked = Object.entries(latest.personas)
    .sort((a, b) => b[1].pnl_pct - a[1].pnl_pct)

  const medals = ['🥇', '🥈', '🥉']

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-950 to-gray-900 text-gray-100">
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="text-center mb-6 md:mb-10">
          <h1 className="text-2xl md:text-4xl font-bold bg-gradient-to-r from-amber-400 to-yellow-300 bg-clip-text text-transparent">
            ⚔️ Portfolio Battle
          </h1>
          <p className="text-gray-400 mt-2 text-xs md:text-base">RM10,000 each · Hourly rebalance · Mon-Fri 9am-5pm</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 md:gap-4 mb-10">
          {ranked.map(([pid, snap], i) => {
            const p = PERSONAS[pid]
            const Icon = ICONS[pid]
            const isWinner = i === 0
            return (
              <div key={pid}
                className="rounded-xl p-5 border-2 transition-all bg-gray-800/50"
                style={{ borderColor: COLORS[pid] + '80' }}
              >
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-2xl">{medals[i]}</span>
                      <span className="text-xl font-bold" style={{ color: COLORS[pid] }}>{p.name}</span>
                    </div>
                    <p className="text-xs text-gray-500 mt-0.5">{p.god} · {p.style}</p>
                  </div>
                  <Icon className={`w-6 h-6 ${isWinner ? 'text-yellow-400' : 'text-gray-500'}`} />
                </div>
                <div className="text-2xl md:text-3xl font-mono font-bold">{formatRM(snap.total)}</div>
                <div className={`flex items-center gap-1 mt-1 text-base md:text-lg font-mono ${snap.pnl_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {snap.pnl_pct >= 0 ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                  {pctStr(snap.pnl_pct)}
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  Cash: {formatRM(snap.cash)} · {Object.keys(snap.holdings).length} holdings
                </div>
                <p className="text-xs text-gray-500 mt-2 italic leading-relaxed">{p.strategy}</p>
              </div>
            )
          })}
        </div>

        <div className="bg-gray-800/30 rounded-xl p-4 md:p-6 border border-gray-700 mb-10">
          <h2 className="text-base md:text-lg font-semibold mb-4 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-emerald-400" />
            Portfolio Value Over Time
          </h2>
          <div className="h-[220px] sm:h-[300px] md:h-[350px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="time" stroke="#6b7280" fontSize={12} />
              <YAxis stroke="#6b7280" fontSize={12} tickFormatter={v => `RM${(v/1000).toFixed(1)}k`} />
              <Tooltip
                contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }}
                formatter={(value: number) => [formatRM(value), '']}
              />
              <Legend />
              {Object.keys(PERSONAS).map(pid => (
                <Line key={pid} type="monotone" dataKey={pid} name={PERSONAS[pid].name}
                  stroke={COLORS[pid]} strokeWidth={2} dot={false} />
              ))}
            </LineChart>
          </ResponsiveContainer>
          </div>
        </div>

        {ranked.map(([pid, snap]) => (
          <div key={pid} className="mb-8">
            <h3 className="text-base md:text-lg font-semibold mb-3 flex items-center gap-2" style={{ color: COLORS[pid] }}>
              {PERSONAS[pid].name} — Holdings
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm min-w-[650px]">
                <thead>
                  <tr className="text-left text-gray-400 border-b border-gray-700">
                    <th className="pb-2 font-medium">Stock</th>
                    <th className="pb-2 font-medium text-right cursor-pointer select-none hover:text-gray-200 transition-colors"
                      onClick={() => toggleSort('shares')}>
                      Shares{sortIcon('shares')}
                    </th>
                    <th className="pb-2 font-medium text-right cursor-pointer select-none hover:text-gray-200 transition-colors"
                      onClick={() => toggleSort('cost')}>
                      Cost{sortIcon('cost')}
                    </th>
                    <th className="pb-2 font-medium text-right cursor-pointer select-none hover:text-gray-200 transition-colors"
                      onClick={() => toggleSort('price')}>
                      Price{sortIcon('price')}
                    </th>
                    <th className="pb-2 font-medium text-right cursor-pointer select-none hover:text-gray-200 transition-colors"
                      onClick={() => toggleSort('current')}>
                      Value{sortIcon('current')}
                    </th>
                    <th className="pb-2 font-medium text-right cursor-pointer select-none hover:text-gray-200 transition-colors"
                      onClick={() => toggleSort('pnl_pct')}>
                      P&amp;L{sortIcon('pnl_pct')}
                    </th>
                    <th className="pb-2 font-medium text-right cursor-pointer select-none hover:text-gray-200 transition-colors"
                      onClick={() => toggleSort('weight')}>
                      Weight{sortIcon('weight')}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {sortHoldings(snap.holdings).map(([name, h]) => (
                    <tr key={name} className="border-b border-gray-800 hover:bg-gray-800/30 cursor-pointer transition-colors"
                      onClick={() => window.location.href = `/stock/${h.code}?persona=${pid}`}>
                      <td className="py-2 font-medium text-emerald-400 hover:text-emerald-300">{name}</td>
                      <td className="py-2 text-right font-mono">{h.shares.toLocaleString()}</td>
                      <td className="py-2 text-right font-mono text-gray-400">RM {h.cost.toFixed(3)}</td>
                      <td className="py-2 text-right font-mono">RM {h.price.toFixed(3)}</td>
                      <td className="py-2 text-right font-mono">{formatRM(h.current)}</td>
                      <td className={`py-2 text-right font-mono ${h.pnl_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                        {pctStr(h.pnl_pct)}
                      </td>
                      <td className="py-2 text-right font-mono text-gray-400">{h.weight}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ))}

        <div className="text-center text-xs text-gray-600 mt-8 flex items-center justify-center gap-1">
          <RefreshCw className="w-3 h-3" />
          Last update: {new Date(latest.timestamp).toLocaleString('en-MY')}
        </div>
      </div>
    </div>
  )
}

function Loading() {
  const shimmer = "bg-gray-700/60 animate-pulse rounded"
  const personas = ['ares', 'demeter', 'athena'] as const
  const headers = ['Stock', 'Shares', 'Cost', 'Price', 'Value', 'P&L', 'Weight']

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-950 to-gray-900 text-gray-100">
      <div className="max-w-6xl mx-auto px-4 py-8">
        {/* Title */}
        <div className="text-center mb-10">
          <div className={`h-10 w-72 mx-auto mb-3 ${shimmer}`} />
          <div className={`h-4 w-96 mx-auto ${shimmer}`} />
        </div>

        {/* Persona cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 md:gap-4 mb-10">
          {personas.map(pid => (
            <div key={pid}
              className="rounded-xl p-5 border-2 border-gray-700/40 bg-gray-800/50"
            >
              <div className="flex items-center justify-between mb-3">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <div className={`w-8 h-8 ${shimmer}`} />
                    <div className={`h-6 w-20 ${shimmer}`} />
                  </div>
                  <div className={`h-3 w-32 ${shimmer}`} />
                </div>
                <div className={`w-6 h-6 ${shimmer}`} />
              </div>
              <div className={`h-8 md:h-9 w-36 mb-2 ${shimmer}`} />
              <div className={`h-5 md:h-6 w-24 mb-1 ${shimmer}`} />
              <div className={`h-3 w-44 mt-1 ${shimmer}`} />
              <div className={`h-9 w-full mt-3 ${shimmer}`} />
            </div>
          ))}
        </div>

        {/* Chart skeleton */}
        <div className="bg-gray-800/30 rounded-xl p-4 md:p-6 border border-gray-700 mb-10">
          <div className={`h-6 w-56 mb-4 ${shimmer}`} />
          <div className={`h-[220px] sm:h-[300px] md:h-[350px] w-full ${shimmer}`} />
        </div>

        {/* Holdings table skeletons */}
        {personas.map(pid => (
          <div key={pid} className="mb-8">
            <div className={`h-6 w-56 mb-3 ${shimmer}`} />
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left border-b border-gray-700">
                    {headers.map(h => (
                      <th key={h} className="pb-2 font-medium">
                        <div className={`h-4 w-14 ${shimmer}`} />
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {Array.from({ length: 3 + Math.floor(Math.random() * 3) }).map((_, i) => (
                    <tr key={i} className="border-b border-gray-800">
                      <td className="py-2"><div className={`h-4 w-20 ${shimmer}`} /></td>
                      <td className="py-2"><div className={`h-4 w-16 ml-auto ${shimmer}`} /></td>
                      <td className="py-2"><div className={`h-4 w-20 ml-auto ${shimmer}`} /></td>
                      <td className="py-2"><div className={`h-4 w-20 ml-auto ${shimmer}`} /></td>
                      <td className="py-2"><div className={`h-4 w-24 ml-auto ${shimmer}`} /></td>
                      <td className="py-2"><div className={`h-4 w-18 ml-auto ${shimmer}`} /></td>
                      <td className="py-2"><div className={`h-4 w-12 ml-auto ${shimmer}`} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ))}

        <div className="text-center mt-8">
          <div className={`h-3 w-48 mx-auto ${shimmer}`} />
        </div>
      </div>
    </div>
  )
}

function Empty() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-950 to-gray-900 flex items-center justify-center">
      <div className="text-center max-w-md mx-auto px-4">
        <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-gray-800 mb-5">
          <Trophy className="w-10 h-10 text-gray-500" />
        </div>
        <h2 className="text-xl font-bold text-gray-300 mb-2">Portfolio Battle Starting Soon</h2>
        <p className="text-gray-500 mb-1">
          The three personas — Ares, Demeter, and Athena — are waiting for the first market cycle.
        </p>
        <p className="text-sm text-gray-600 mb-6">
          Battles run every 30 minutes on Wed–Fri, 9am–5pm MYT.
          Once trading begins, portfolio snapshots and live prices will appear here.
        </p>
        <a
          href="/watchlist"
          className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-700 rounded-lg transition-colors"
        >
          Browse Watchlist
          <ArrowRight className="w-4 h-4" />
        </a>
      </div>
    </div>
  )
}

function ErrorMsg({ msg }: { msg: string }) {
  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-950">
      <div className="text-center">
        <p className="text-red-400">Error loading data: {msg}</p>
      </div>
    </div>
  )
}
