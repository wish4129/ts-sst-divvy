import { useState, useEffect } from 'react'
import { Trophy, TrendingUp, TrendingDown, Shield, Zap, Scale, RefreshCw } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'

const API_URL = import.meta.env.VITE_API_URL || ''

interface StockHolding {
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
        <div className="text-center mb-10">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-amber-400 to-yellow-300 bg-clip-text text-transparent">
            ⚔️ Portfolio Battle
          </h1>
          <p className="text-gray-400 mt-2">RM10,000 each · Hourly rebalance · Mon-Fri 9am-5pm</p>
        </div>

        <div className="grid grid-cols-3 gap-4 mb-10">
          {ranked.map(([pid, snap], i) => {
            const p = PERSONAS[pid]
            const Icon = ICONS[pid]
            const isWinner = i === 0
            return (
              <div key={pid}
                className={`rounded-xl p-5 border-2 transition-all ${
                  isWinner
                    ? 'border-yellow-500/50 bg-yellow-500/5 shadow-lg shadow-yellow-500/10'
                    : 'border-gray-700 bg-gray-800/50'
                }`}
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
                <div className="text-3xl font-mono font-bold">{formatRM(snap.total)}</div>
                <div className={`flex items-center gap-1 mt-1 text-lg font-mono ${snap.pnl_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
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

        <div className="bg-gray-800/30 rounded-xl p-6 border border-gray-700 mb-10">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-emerald-400" />
            Portfolio Value Over Time
          </h2>
          <ResponsiveContainer width="100%" height={350}>
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

        {ranked.map(([pid, snap]) => (
          <div key={pid} className="mb-8">
            <h3 className="text-lg font-semibold mb-3 flex items-center gap-2" style={{ color: COLORS[pid] }}>
              {PERSONAS[pid].name} — Holdings
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-400 border-b border-gray-700">
                    <th className="pb-2 font-medium">Stock</th>
                    <th className="pb-2 font-medium text-right">Shares</th>
                    <th className="pb-2 font-medium text-right">Cost</th>
                    <th className="pb-2 font-medium text-right">Price</th>
                    <th className="pb-2 font-medium text-right">Value</th>
                    <th className="pb-2 font-medium text-right">P&L</th>
                    <th className="pb-2 font-medium text-right">Weight</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(snap.holdings).map(([name, h]) => (
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
  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-950">
      <div className="text-center">
        <Trophy className="w-12 h-12 text-yellow-500 mx-auto mb-4 animate-pulse" />
        <p className="text-gray-400">Loading battle data...</p>
      </div>
    </div>
  )
}

function Empty() {
  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-950">
      <div className="text-center">
        <Trophy className="w-12 h-12 text-gray-600 mx-auto mb-4" />
        <p className="text-gray-400">No battle data yet</p>
        <p className="text-gray-600 text-sm mt-1">First run starts at next market hour</p>
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
