import { useParams, useSearchParams, Link } from 'react-router-dom'
import { useState, useMemo } from 'react'
import { Helmet } from 'react-helmet-async'
import { ArrowLeft, Brain, ChevronDown, ChevronRight, ExternalLink, CheckSquare, Square } from 'lucide-react'
import { seo } from '../lib/seo'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import ScoreBadge from '../components/ScoreBadge'
import SparklineChart from '../components/SparklineChart'
import { INDUSTRY_COLORS } from '../data/stocks'
import { useApi } from '../hooks/useApi'
import type { Stock } from '../data/stocks'

// Ticker → short code reverse map (same as Watchlist)
const TICKER_TO_SHORT: Record<string, string> = {
  '1155.KL': 'MAYBANK', '6742.KL': 'YTLPOWR', '5106.KL': 'AXREIT',
  '3379.KL': 'INSAS', '7089.KL': 'LIIHEN', '4731.KL': 'SCIENTEX',
  '0104.KL': 'GENETEC', '2445.KL': 'KLK', '0166.KL': 'INARI',
  '4197.KL': 'SIME', '7087.KL': 'MAGNI', '5983.KL': 'MBMR',
  '5293.KL': 'AME', '5132.KL': 'DELEUM', '5142.KL': 'WASCO',
  '5280.KL': 'KIPREIT', 'INTA.KL': 'INTA',
  '1066.KL': 'RHB', '7052.KL': 'PADINI',
  '5398.KL': 'GAMUDA', '5236.KL': 'MATRIX',
  '1295.KL': 'PBBANK', '5031.KL': 'TIME', '0099.KL': 'SCICOM',
  '5250.KL': 'SEM',
}

interface TriggerItem {
  text: string
  active: boolean
  source_url?: string
}

interface PersonaAnalysis {
  persona: string
  stock_name: string
  industry: string
  score_composite: number
  score_breakdown: Record<string, { value: number | null; raw: number; weighted: number }>
  rationale: {
    sections: Record<string, any>
    sources: Record<string, string>
  }
  kronos_signal: any
  ai_report: Record<string, string> | null
  ai_model: string | null
  generated_at: string
  financials?: any[]
  last_price?: number
  price_change?: number
  market_cap?: number
  dividend_yield?: number
  sparkline?: number[]
}

// ── Default source labels ──
const DEFAULT_SOURCES: Record<string, string> = {
  'Strategic Fit': 'Portfolio strategy rules + Kronos forecast',
  'Score Analysis': 'Industry matrix + quarterly financials (yfinance)',
  'Kronos AI 30-Day Forecast': 'Kronos-small model (NeoQuasar/Kronos)',
  'Macro Context': 'Yahoo Finance macro signals',
  'Risk Factors': 'Quarterly reports + Kronos volatility',
  'Action Triggers': 'Persona trading rules (portfolios.json)',
}

const AI_REPORT_LABELS: Record<string, string> = {
  introduction_history: 'Introduction & History',
  trend_analysis: 'Trend Analysis',
  strengths: 'Strengths',
  weaknesses: 'Weaknesses',
  summary: 'Summary',
  target: 'Price Target & Cut Loss',
  price_target: 'Price Target',
  cut_loss: 'Cut Loss',
}

function AiReportSection({ report, model }: { report: Record<string, string>; model: string | null }) {
  const [open, setOpen] = useState(true)
  
  // Normalize: merge price_target + cut_loss into target if target is missing
  const normalized = { ...report }
  if (!normalized.target && (normalized.price_target || normalized.cut_loss)) {
    normalized.target = [
      normalized.price_target,
      normalized.cut_loss,
    ].filter(Boolean).join('\n')
    delete normalized.price_target
    delete normalized.cut_loss
  }
  
  const sectionOrder = ['introduction_history', 'trend_analysis', 'strengths', 'weaknesses', 'summary', 'target']
  const sections = sectionOrder.filter(k => normalized[k])
  
  return (
    <div>
      <button onClick={() => setOpen(!open)} aria-expanded={open}
        className="w-full flex items-center gap-2 px-5 py-3 text-left hover:bg-emerald-100/30 dark:hover:bg-emerald-900/20 transition-colors">
        {open ? <ChevronDown className="w-4 h-4 text-emerald-500" /> : <ChevronRight className="w-4 h-4 text-emerald-500" />}
        <Brain className="w-4 h-4 text-emerald-500" />
        <span className="text-xs font-semibold text-emerald-700 dark:text-emerald-400 uppercase tracking-wide">AI Analysis Report</span>
        {model && <span className="text-[10px] text-gray-400 ml-auto">via {model}</span>}
      </button>
      {open && (
        <div className="px-5 pb-4 space-y-4">
          {sections.map(key => {
            const text = normalized[key]
            return (
            <div key={key}>
              <h4 className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 mb-1">{AI_REPORT_LABELS[key] || key}</h4>
              <div className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed space-y-1">
                {text.split('\n').map((line: string, i: number) => (
                  <RenderLine key={i} line={line} />
                ))}
              </div>
            </div>
          )})}
        </div>
      )}
    </div>
  )
}

function RenderLine({ line }: { line: string }) {
  if (!line.trim()) return <div className="h-2" />
  
  // Bullet points — detect and strip prefix
  const trimmed = line.trimStart()
  const indent = line.length - trimmed.length
  const isBullet = /^[-•*]\s/.test(trimmed)
  
  // Strip bullet prefix before parsing bold markers
  const content = isBullet ? trimmed.replace(/^[-•*]\s+/, '') : trimmed
  
  // Bold: **text**
  const parts = content.split(/(\*\*[^*]+\*\*)/g)
  const rendered = parts.map((p, i) => {
    if (p.startsWith('**') && p.endsWith('**')) {
      return <strong key={i} className="text-gray-900 dark:text-gray-100">{p.slice(2, -2)}</strong>
    }
    return <span key={i}>{p}</span>
  })
  
  return (
    <div style={{ paddingLeft: `${indent * 4 + (isBullet ? 16 : 0)}px` }}
         className={isBullet ? 'flex items-start gap-2' : ''}>
      {isBullet && <span className="text-emerald-400 flex-shrink-0 mt-1">•</span>}
      <span>{rendered}</span>
    </div>
  )
}

function AnalysisSections({ analysis }: { analysis: PersonaAnalysis }) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})
  
  // Parse — may be JSON string from DB
  let data: { sections?: Record<string, any>; sources?: Record<string, string> } = {}
  try {
    const raw = typeof analysis.rationale === 'string' 
      ? JSON.parse(analysis.rationale) 
      : analysis.rationale
    data = raw || {}
  } catch { data = {} }

  const sections = data.sections || {}
  const sources = data.sources || {}

  const sectionKeys = Object.keys(sections)
  if (!sectionKeys.length) return null

  const toggle = (section: string) => setExpanded(prev => ({ ...prev, [section]: !prev[section] }))

  return (
    <div className="divide-y divide-emerald-200/50 dark:divide-emerald-800/50">
      {sectionKeys.map((section, i) => {
        const content = sections[section]
        const isOpen = expanded[section] ?? (i < 2)
        const sourceUrl = sources[section] || ''
        const sourceLabel = DEFAULT_SOURCES[section] || ''

        return (
          <div key={section}>
            <button
              onClick={() => toggle(section)}
              aria-expanded={isOpen}
              className="w-full flex items-center gap-2 px-5 py-3 text-left hover:bg-emerald-100/30 dark:hover:bg-emerald-900/20 transition-colors"
            >
              {isOpen ? <ChevronDown className="w-4 h-4 text-emerald-500 flex-shrink-0" /> : <ChevronRight className="w-4 h-4 text-emerald-500 flex-shrink-0" />}
              <span className="text-xs font-semibold text-emerald-700 dark:text-emerald-400 uppercase tracking-wide">{section}</span>
              <span className="text-[10px] text-gray-400 ml-auto hidden sm:inline">{sourceLabel}</span>
            </button>
            {isOpen && (
              <div className="px-5 pb-4">
                {/* Action Triggers: checkboxes */}
                {Array.isArray(content) && content.length > 0 && typeof content[0] === 'object' && 'text' in content[0] ? (
                  <div className="space-y-2">
                    {(content as TriggerItem[]).map((t, j) => (
                      <div key={j} className="flex items-start gap-2">
                        {t.active 
                          ? <CheckSquare className="w-4 h-4 text-emerald-500 mt-0.5 flex-shrink-0" />
                          : <Square className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" />
                        }
                        <span className={`text-sm ${t.active ? 'text-emerald-700 dark:text-emerald-400 font-medium' : 'text-gray-600 dark:text-gray-400'}`}>
                          {t.text}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : Array.isArray(content) ? (
                  /* Bullet point list */
                  <ul className="space-y-1.5">
                    {content.map((item: string, j: number) => (
                      <li key={j} className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed flex items-start gap-2">
                        <span className="text-emerald-400 mt-1.5 flex-shrink-0">•</span>
                        <span>{String(item)}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  /* Fallback: plain text */
                  <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">{String(content)}</p>
                )}
                
                {/* Source link */}
                <div className="flex items-center gap-1 mt-3 pt-2 border-t border-emerald-100 dark:border-emerald-800/30">
                  <span className="text-[10px] text-gray-400 sm:hidden">{sourceLabel}</span>
                  {sourceUrl && (
                    <a href={sourceUrl} target="_blank" rel="noopener noreferrer"
                       className="inline-flex items-center gap-1 text-[10px] text-emerald-500 hover:text-emerald-600 ml-auto">
                      <ExternalLink className="w-3 h-3" /> Reference
                    </a>
                  )}
                </div>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}


export default function StockDetail() {
  const { code } = useParams<{ code: string }>()
  const [searchParams] = useSearchParams()
  const persona = searchParams.get('persona')

  const url = useMemo(() => {
    if (!code) return null
    return persona
      ? `/analysis/${code}?persona=${persona}`
      : `/analysis/${code}`
  }, [code, persona])

  const api = useApi<PersonaAnalysis>(url)

  // Build display stock from API analysis data (no static stocks.ts dependency)
  const displayStock: Stock = useMemo(() => {
    const shortCode = code ? (TICKER_TO_SHORT[code] || code.toUpperCase()) : ''
    if (api.data) {
      return {
        code: shortCode,
        name: api.data.stock_name || code || '',
        industry: api.data.industry || '',
        marketCap: api.data.market_cap || 0,
        lastPrice: api.data.last_price || 0,
        priceChange: api.data.price_change || 0,
        dividendYield: api.data.dividend_yield || 0,
        score: {
          composite: api.data.score_composite || 0,
          dividend: api.data.score_breakdown?.dividend_yield?.raw || 0,
          growth: api.data.score_breakdown?.revenue_growth_yoy?.raw || 0,
          quality: api.data.score_breakdown?.roe?.raw || 0,
          risk: api.data.score_breakdown?.de_ratio?.raw || 0,
        },
        financials: api.data.financials || [],
        dividends: [],
        sparkline: api.data.sparkline || [],
        status: (api.data.score_composite || 0) >= 70 ? 'active' as const : 'revisit' as const,
        addedAt: '',
        revisitAt: null,
        notes: '',
      }
    }
    // Before analysis loads — minimal placeholder
    return {
      code: shortCode,
      name: shortCode || code || 'Loading...',
      industry: '',
      marketCap: 0,
      lastPrice: 0,
      priceChange: 0,
      dividendYield: 0,
      score: { composite: 0, dividend: 0, growth: 0, quality: 0, risk: 0 },
      financials: [],
      dividends: [],
      status: 'revisit',
      addedAt: '',
      revisitAt: null,
      notes: '',
      sparkline: [],
    }
  }, [api.data, code])

  if (!code) {
    return (
      <div className="min-h-screen">
        <Helmet {...seo({
          title: 'Stock not found — Divvy Bursa Tracker',
          description: 'The requested stock could not be found.',
          noindex: true,
        })} />
        <main className="max-w-3xl mx-auto px-4 py-20 text-center">
          <h1 className="text-2xl font-bold text-gray-400 mb-2">Stock not found</h1>
          <Link to="/" className="text-emerald-600 hover:text-emerald-700">Back to Dashboard</Link>
        </main>
      </div>
    )
  }

  if (api.loading) return <StockDetailSkeleton />

  const indColor = INDUSTRY_COLORS[displayStock.industry] || 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200'
  const changeColor = displayStock.priceChange >= 0 ? 'text-emerald-600' : 'text-red-500'
  const changeIcon = displayStock.priceChange >= 0 ? '▲' : '▼'
  const divData = displayStock.dividends.map((d) => ({ date: d.exDate.slice(0, 7), amount: d.amount, yield: d.yield }))

  return (
    <div className="min-h-screen">
      <Helmet {...seo({
        title: `${displayStock.name} (${displayStock.code}) — Stock Analysis | Divvy`,
        description: `Deep analysis of ${displayStock.name} (${displayStock.code}). ${displayStock.industry} stock with composite score ${displayStock.score.composite}/100, RM ${displayStock.lastPrice.toFixed(2)} last price, DY ${displayStock.dividendYield}%. Bursa Malaysia investment tracker.`,
        canonical: `https://d2d7b6u77b6we4.cloudfront.net/stock/${code}`,
      })} />
      <main className="max-w-4xl mx-auto px-4 py-6">
        <Link to="/battle" aria-label="Back to Battle" className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 mb-4">
          <ArrowLeft className="w-4 h-4" /> Back to Battle
        </Link>

        <div className="flex flex-wrap items-start justify-between gap-3 md:gap-4 mb-4 md:mb-6">
          <div>
            <div className="flex items-center gap-2 md:gap-3 mb-1">
              <h1 className="text-xl md:text-2xl font-bold text-gray-900 dark:text-gray-100">{displayStock.name}</h1>
              {displayStock.industry && (
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${indColor}`}>{displayStock.industry}</span>
              )}
            </div>
            <p className="text-xs md:text-sm text-gray-500">{displayStock.code} · MCap RM {displayStock.marketCap}B</p>
          </div>
          <div className="flex items-center gap-3 md:gap-4">
            <div className="text-right">
              <span className="text-2xl md:text-3xl font-bold text-gray-900 dark:text-gray-100">RM {displayStock.lastPrice.toFixed(2)}</span>
              <span className={`ml-2 text-sm font-medium ${changeColor}`}>{changeIcon} {Math.abs(displayStock.priceChange).toFixed(2)}%</span>
            </div>
            <ScoreBadge score={displayStock.score.composite} size="lg" />
          </div>
        </div>

        {/* Persona Analysis Banner — AI Report right after stock title */}
        {api.data && (
          <div className="mb-6 rounded-xl border-2 border-emerald-500/30 bg-emerald-50/50 dark:bg-emerald-950/20 dark:border-emerald-500/20 overflow-hidden">
            <div className="p-5 border-b border-emerald-200 dark:border-emerald-800">
              <div className="flex items-center gap-2">
                <Brain className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
                <h2 className="font-bold text-emerald-800 dark:text-emerald-300 capitalize">{api.data.persona}'s Deep Analysis</h2>
                <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-900 text-emerald-700 dark:text-emerald-300">
                  Score {api.data.score_composite}/100
                </span>
                <span className="text-xs text-gray-400 ml-auto">
                  {api.data.generated_at ? new Date(api.data.generated_at).toLocaleDateString('en-MY', { day: 'numeric', month: 'short', year: 'numeric' }) : ''}
                </span>
              </div>
            </div>

            <AnalysisSections analysis={api.data} />

            {/* AI Analysis Report */}
            {api.data.ai_report && (
              <div className="divide-y divide-emerald-200/50 dark:divide-emerald-800/50 border-t border-emerald-200 dark:border-emerald-800">
                <AiReportSection report={api.data.ai_report} model={api.data.ai_model} />
              </div>
            )}

            {/* Factor breakdown */}
            {api.data.score_breakdown && (
              <div className="p-5 border-t border-emerald-200 dark:border-emerald-800">
                <h3 className="text-xs font-semibold text-emerald-700 dark:text-emerald-400 uppercase tracking-wide mb-2">
                  Factor Score Breakdown
                  <span className="text-[10px] text-gray-400 ml-2 font-normal normal-case">Source: Quarterly financials (yfinance)</span>
                </h3>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                  {Object.entries(api.data.score_breakdown).map(([factor, b]: [string, any]) => (
                    <div key={factor} className="flex items-center justify-between text-xs bg-white/50 dark:bg-black/20 rounded px-2 py-1">
                      <span className="text-gray-500 capitalize truncate mr-2">{factor.replace(/_/g, ' ')}</span>
                      <span className="font-mono text-gray-700 dark:text-gray-300 flex-shrink-0">
                        {b.weighted?.toFixed(1) || '—'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
          <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-800">
            <h2 className="font-semibold text-sm text-gray-700 dark:text-gray-300 mb-3">Score Breakdown</h2>
            {[
              { label: 'Dividend', value: displayStock.score.dividend, max: 40, color: 'bg-emerald-500' },
              { label: 'Growth', value: displayStock.score.growth, max: 30, color: 'bg-blue-500' },
              { label: 'Quality', value: displayStock.score.quality, max: 20, color: 'bg-violet-500' },
              { label: 'Risk', value: displayStock.score.risk, max: 10, color: 'bg-amber-500' },
            ].map((factor) => (
              <div key={factor.label} className="flex items-center gap-3 mb-2">
                <span className="text-xs text-gray-500 w-16">{factor.label}</span>
                <div className="flex-1 h-2 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                  <div className={`h-full ${factor.color} rounded-full transition-all`}
                    style={{ width: `${(factor.value / factor.max) * 100}%` }} />
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
                {displayStock.sparkline.length > 0
                  ? `RM ${Math.min(...displayStock.sparkline).toFixed(2)} – RM ${Math.max(...displayStock.sparkline).toFixed(2)}`
                  : 'No price data available'}
              </span>
              <span className="text-xs text-gray-500">DY {displayStock.dividendYield}%</span>
            </div>
            <SparklineChart data={displayStock.sparkline} width={300} height={60} />
          </div>
        </div>

        <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-800 mb-6">
          <h2 className="font-semibold text-sm text-gray-700 dark:text-gray-300 mb-3">Quarterly Financials</h2>
          {displayStock.financials.length === 0 ? (
            <p className="text-xs text-gray-400 py-4">Financial data will appear after the next pipeline run.</p>
          ) : (
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
                  {displayStock.financials.map((f) => (
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
          )}
        </div>

        <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-800 mb-6">
          <h2 className="font-semibold text-sm text-gray-700 dark:text-gray-300 mb-3">Dividend History</h2>
          {divData.length === 0 ? (
            <p className="text-xs text-gray-400 py-4">Dividend data will appear after the next pipeline run.</p>
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={divData}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-gray-200 dark:stroke-gray-700" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} className="text-gray-500" />
                <YAxis tick={{ fontSize: 11 }} className="text-gray-500" />
                <Tooltip contentStyle={{
                  backgroundColor: 'var(--tooltip-bg, #fff)',
                  border: '1px solid #e5e7eb',
                  borderRadius: '8px',
                  fontSize: '12px',
                }} />
                <Bar dataKey="amount" fill="#059669" radius={[4, 4, 0, 0]} name="DPS (RM)" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </main>
    </div>
  )
}

function StockDetailSkeleton() {
  const shimmer = "bg-gray-200 dark:bg-gray-700 animate-pulse rounded"

  return (
    <div role="status" aria-live="polite" className="min-h-screen">
      <main className="max-w-4xl mx-auto px-4 py-6">
        {/* Back link */}
        <div className={`h-4 w-24 mb-4 ${shimmer}`} />

        {/* Title + price + score */}
        <div className="flex flex-wrap items-start justify-between gap-3 md:gap-4 mb-4 md:mb-6">
          <div>
            <div className="flex items-center gap-2 md:gap-3 mb-1">
              <div className={`h-7 md:h-8 w-48 ${shimmer}`} />
              <div className={`h-5 w-20 rounded-full ${shimmer}`} />
            </div>
            <div className={`h-3 md:h-4 w-40 mt-1 ${shimmer}`} />
          </div>
          <div className="flex items-center gap-3 md:gap-4">
            <div className="text-right">
              <div className={`h-8 md:h-9 w-28 mb-1 ${shimmer}`} />
              <div className={`h-4 w-16 ml-auto ${shimmer}`} />
            </div>
            <div className="w-12 h-12 rounded-full bg-gray-200 dark:bg-gray-700 animate-pulse" />
          </div>
        </div>

        {/* Analysis banner skeleton */}
        <div className="mb-6 rounded-xl border-2 border-emerald-500/20 bg-emerald-50/30 dark:bg-emerald-950/10 overflow-hidden">
          <div className="p-5">
            <div className="flex items-center gap-2">
              <div className={`h-5 w-5 ${shimmer}`} />
              <div className={`h-5 w-40 ${shimmer}`} />
              <div className={`h-5 w-20 rounded-full ${shimmer}`} />
            </div>
          </div>
          <div className="p-5 space-y-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i}>
                <div className={`h-4 w-32 mb-1 ${shimmer}`} />
                <div className={`h-4 w-full ${shimmer}`} />
              </div>
            ))}
          </div>
        </div>

        {/* Score breakdown + chart */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
          <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-800">
            <div className={`h-5 w-32 mb-3 ${shimmer}`} />
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="flex items-center gap-3 mb-2">
                <div className={`h-4 w-16 ${shimmer}`} />
                <div className={`flex-1 h-2 ${shimmer}`} />
                <div className={`h-4 w-8 ${shimmer}`} />
              </div>
            ))}
          </div>
          <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-800">
            <div className={`h-5 w-40 mb-3 ${shimmer}`} />
            <div className={`h-[60px] w-full ${shimmer}`} />
          </div>
        </div>

        {/* Financials table skeleton */}
        <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-800 mb-6">
          <div className={`h-5 w-40 mb-3 ${shimmer}`} />
          <div className="space-y-2">
            <div className="flex gap-2">
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className={`h-4 flex-1 ${shimmer}`} />
              ))}
            </div>
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="flex gap-2">
                {Array.from({ length: 8 }).map((_, j) => (
                  <div key={j} className={`h-4 flex-1 ${shimmer}`} />
                ))}
              </div>
            ))}
          </div>
        </div>

        {/* Dividend chart skeleton */}
        <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-800 mb-6">
          <div className={`h-5 w-36 mb-3 ${shimmer}`} />
          <div className={`h-[200px] w-full ${shimmer}`} />
        </div>
      </main>
    </div>
  )
}
