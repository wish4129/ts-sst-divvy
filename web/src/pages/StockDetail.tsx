import { useParams, Link } from 'react-router-dom'
import { useState, useMemo } from 'react'
import { Helmet } from 'react-helmet-async'
import { ArrowLeft, Brain, ChevronDown, ChevronRight } from 'lucide-react'
import { seo } from '../lib/seo'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import ScoreBadge from '../components/ScoreBadge'
import SparklineChart from '../components/SparklineChart'
import { INDUSTRY_COLORS, TICKER_TO_SHORT } from '../data/stocks'
import { useApi } from '../hooks/useApi'
import type { Stock } from '../data/stocks'

interface AnalysisData {
  stock_name: string
  industry: string
  score_composite: number
  score_breakdown: Record<string, { value: number | null; raw: number; weighted: number }>
  ai_report: Record<string, string> | null
  ai_model: string | null
  generated_at: string
  financials?: any[]
  last_price?: number
  price_change?: number
  market_cap?: number
  dividend_yield?: number
  sparkline?: number[]
  pivot_tag?: string | null
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
  // 5-section format keys (preview sections)
  overview: 'Overview',
  risk_assessment: 'Risk Assessment',
  financial_health: 'Financial Health',
  growth_prospects: 'Growth Prospects',
}

// Keys that are preview (shown open) vs gated (shown with lock)
const PREVIEW_SECTION_KEYS = new Set(['overview', 'risk_assessment', 'financial_health', 'growth_prospects', 'introduction_history', 'trend_analysis', 'strengths', 'weaknesses', 'summary'])
const GATED_SECTION_KEYS = new Set(['target', 'price_target', 'cut_loss'])

function AiReportSection({ report, model, generatedAt }: { report: Record<string, string>; model: string | null; generatedAt?: string }) {
  const [open, setOpen] = useState(true)

  const normalized = { ...report }
  if (!normalized.target && (normalized.price_target || normalized.cut_loss)) {
    normalized.target = [normalized.price_target, normalized.cut_loss].filter(Boolean).join('\n')
    delete normalized.price_target
    delete normalized.cut_loss
  }

  const previewSections = Object.entries(normalized).filter(([k]) => PREVIEW_SECTION_KEYS.has(k))
  const gatedSections = Object.entries(normalized).filter(([k]) => GATED_SECTION_KEYS.has(k))

  const formattedDate = generatedAt
    ? new Date(generatedAt).toLocaleDateString('en-MY', { day: 'numeric', month: 'short', year: 'numeric' })
    : null

  const renderSection = ([key, content]: [string, string]) => (
    <div key={key} className="border-l-2 border-emerald-200 dark:border-emerald-700/50 pl-3">
      <h4 className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 mb-1.5">{AI_REPORT_LABELS[key] || key}</h4>
      <div className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed space-y-1">
        {content.split('\n').map((line: string, i: number) => (
          <RenderLine key={i} line={line} />
        ))}
      </div>
    </div>
  )

  return (
    <div>
      <button onClick={() => setOpen(!open)} aria-expanded={open}
        className="w-full flex items-center gap-2 px-4 sm:px-5 py-3 sm:py-3 text-left hover:bg-emerald-100/30 dark:hover:bg-emerald-900/20 transition-colors min-h-[44px]">
        {open ? <ChevronDown className="w-4 h-4 text-emerald-500" /> : <ChevronRight className="w-4 h-4 text-emerald-500" />}
        <Brain className="w-4 h-4 text-emerald-500" />
        <span className="text-xs font-semibold text-emerald-700 dark:text-emerald-400 uppercase tracking-wide">AI Analysis Report</span>
        {model && <span className="text-[10px] text-gray-400 dark:text-gray-500 ml-auto">via {model}</span>}
      </button>
      {open && (
        <div className="px-5 pb-4 space-y-5">
          {/* Preview sections — shown first */}
          {previewSections.map(renderSection)}

          {/* Meta line — between preview and gated */}
          {formattedDate && gatedSections.length > 0 && (
            <div className="text-xs text-gray-400 dark:text-gray-500 border-t border-emerald-200/50 dark:border-emerald-800/50 pt-4 mt-4">
              Covered by analysis on {formattedDate}
            </div>
          )}

          {/* Gated sections — shown after meta with lock indicator */}
          {gatedSections.length > 0 && (
            <div className="space-y-5">
              <div className="flex items-center gap-1.5 text-xs text-amber-600 dark:text-amber-400 font-medium">
                <span className="text-amber-500">🔒</span>
                <span>Gated analysis — subscribe to unlock full details</span>
              </div>
              {gatedSections.map(renderSection)}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function RenderLine({ line }: { line: string }) {
  if (!line.trim()) return <div className="h-2" />
  const trimmed = line.trimStart()
  const indent = line.length - trimmed.length
  // Support bullets (-, *, •) AND numbered items (1., 2., etc.)
  const isBullet = /^[-•*]\s/.test(trimmed)
  const isNumbered = /^\d+\.\s/.test(trimmed)
  const content = isBullet ? trimmed.replace(/^[-•*]\s+/, '') :
                  isNumbered ? trimmed.replace(/^\d+\.\s+/, '') : trimmed

  const parts = content.split(/(\*\*[^*]+\*\*)/g)
  const rendered = parts.map((p, i) => {
    if (p.startsWith('**') && p.endsWith('**')) {
      return <strong key={i} className="text-gray-900 dark:text-gray-100">{p.slice(2, -2)}</strong>
    }
    return <span key={i}>{p}</span>
  })

  return (
    <div style={{ paddingLeft: `${indent * 4 + ((isBullet || isNumbered) ? 20 : 0)}px` }}
         className={(isBullet || isNumbered) ? 'flex items-start gap-2' : ''}>
      {(isBullet || isNumbered) && (
        <span className="text-emerald-400 flex-shrink-0 mt-1 text-xs font-mono min-w-[12px]">
          {isNumbered ? trimmed.match(/^\d+/)?.[0] : '•'}
        </span>
      )}
      <span>{rendered}</span>
    </div>
  )
}

export default function StockDetail() {
  const { code } = useParams<{ code: string }>()

  const url = useMemo(() => code ? `/analysis/${code}` : null, [code])
  const api = useApi<AnalysisData>(url)

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
        },
        financials: api.data.financials || [],
        dividends: [],
        sparkline: api.data.sparkline || [],
        pivotTag: api.data.pivot_tag || null,
        status: (api.data.score_composite || 0) >= 70 ? 'active' as const : 'revisit' as const,
        addedAt: '',
        revisitAt: null,
        notes: '',
      }
    }
    return {
      code: shortCode, name: shortCode || code || 'Loading...', industry: '',
      marketCap: 0, lastPrice: 0, priceChange: 0, dividendYield: 0,
      score: { composite: 0 },
      financials: [], dividends: [], status: 'revisit', addedAt: '', revisitAt: null, notes: '', sparkline: [],
    }
  }, [api.data, code])

  const shortCode = code ? (TICKER_TO_SHORT[code] || code.toUpperCase()) : ''
  const indColor = INDUSTRY_COLORS[displayStock.industry] || 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200'
  const changeColor = displayStock.priceChange >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-500 dark:text-red-400'
  const changeIcon = displayStock.priceChange >= 0 ? '▲' : '▼'
  const divData = displayStock.dividends.map((d) => ({ date: d.exDate.slice(0, 7), amount: d.amount, yield: d.yield }))

  const productSchema = useMemo(() => ({
    '@context': 'https://schema.org',
    '@type': 'Product',
    name: `${displayStock.name} (${displayStock.code})`,
    description: `${displayStock.name} is a ${displayStock.industry} stock listed on Bursa Malaysia with the ticker ${displayStock.code}.`,
    identifier: displayStock.code,
    industry: displayStock.industry,
    offers: {
      '@type': 'Offer',
      price: displayStock.lastPrice,
      priceCurrency: 'MYR',
      availability: 'https://schema.org/InStock',
    },
  }), [displayStock])

  const organizationSchema = useMemo(() => ({
    '@context': 'https://schema.org',
    '@type': 'Organization',
    name: displayStock.name,
    identifier: displayStock.code,
    description: `${displayStock.name} (${displayStock.code}) is a ${displayStock.industry} company listed on Bursa Malaysia.`,
  }), [displayStock])

  if (!code) {
    return (
      <div className="min-h-screen">
        <Helmet {...seo({ title: 'Stock not found — Divvy Bursa Tracker', description: 'The requested stock could not be found.', noindex: true })} />
        <main className="max-w-3xl mx-auto px-4 py-20 text-center">
          <h1 className="text-2xl font-bold text-gray-400 mb-2">Stock not found</h1>
          <Link to="/" className="text-emerald-600 hover:text-emerald-700">Back to Dashboard</Link>
        </main>
      </div>
    )
  }

  if (api.loading) return <StockDetailSkeleton />

  return (
    <div className="min-h-screen">
      <Helmet {...seo({
        title: `${displayStock.name} (${displayStock.code}) — Stock Analysis | Divvy`,
        description: `Deep analysis of ${displayStock.name} (${displayStock.code}). ${displayStock.industry} stock with composite score ${displayStock.score.composite}/100, RM ${displayStock.lastPrice.toFixed(2)} last price, DY ${displayStock.dividendYield}%. Bursa Malaysia investment tracker.`,
        canonical: `https://d2d7b6u77b6we4.cloudfront.net/stock/${code}/`,
      })}>
        <script type="application/ld+json">{JSON.stringify(productSchema)}</script>
        <script type="application/ld+json">{JSON.stringify(organizationSchema)}</script>
      </Helmet>
      <main className="max-w-4xl mx-auto px-4 py-6">
        <Link to="/" aria-label="Back to Dashboard" className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 mb-4 min-h-[44px] min-w-[44px]">
          <ArrowLeft className="w-4 h-4" /> Back to Dashboard
        </Link>

        {/* Header — mobile: stack vertically with proper touch padding */}
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 md:gap-4 mb-4 md:mb-6">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-1.5 md:gap-3 mb-1">
              <h1 className="text-xl md:text-2xl font-bold text-gray-900 dark:text-gray-100 break-words">{displayStock.name}</h1>
              {displayStock.industry && (
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${indColor}`}>{displayStock.industry}</span>
              )}
              {displayStock.pivotTag && (
                <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-400 border border-amber-300 dark:border-amber-700" title="Sector pivot / transition">
                  {displayStock.pivotTag}
                </span>
              )}
            </div>
            <p className="text-xs md:text-sm text-gray-500">{displayStock.code} · MCap RM {displayStock.marketCap}B</p>
          </div>
          <div className="flex items-center gap-3 md:gap-4 self-start">
            <div className="text-right">
              <span className="text-2xl md:text-3xl font-bold text-gray-900 dark:text-gray-100">RM {displayStock.lastPrice.toFixed(2)}</span>
              <span className={`ml-2 text-sm font-medium ${changeColor}`}>{changeIcon} {Math.abs(displayStock.priceChange).toFixed(2)}%</span>
            </div>
            <ScoreBadge score={displayStock.score.composite} size="md" className="md:hidden" />
            <ScoreBadge score={displayStock.score.composite} size="lg" className="hidden md:inline-flex" />
          </div>
        </div>

        {/* AI Analysis Report */}
        {api.data && (
          <div className="mb-6 rounded-xl border-2 border-emerald-500/30 bg-emerald-50/50 dark:bg-emerald-950/20 dark:border-emerald-500/20 overflow-hidden">
            <div className="p-5 border-b border-emerald-200 dark:border-emerald-800">
              <div className="flex flex-wrap items-center gap-2">
                <Brain className="w-5 h-5 text-emerald-600 dark:text-emerald-400 flex-shrink-0" />
                <h2 className="font-bold text-emerald-800 dark:text-emerald-300 text-sm sm:text-base">Deep Analysis</h2>
                <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-900 text-emerald-700 dark:text-emerald-300 whitespace-nowrap">
                  Score {api.data.score_composite}/100
                </span>
                <span className="text-[10px] sm:text-xs text-gray-400 sm:ml-auto w-full sm:w-auto mt-1 sm:mt-0">
                  {api.data.generated_at ? new Date(api.data.generated_at).toLocaleDateString('en-MY', { day: 'numeric', month: 'short', year: 'numeric' }) : ''}
                </span>
              </div>
            </div>

            {api.data.ai_report && Object.keys(api.data.ai_report).length > 0 ? (
              <div className="divide-y divide-emerald-200/50 dark:divide-emerald-800/50">
                <AiReportSection report={api.data.ai_report} model={api.data.ai_model} generatedAt={api.data.generated_at} />
              </div>
            ) : (
              <div className="p-5 text-center">
                <p className="text-sm text-gray-400 dark:text-gray-500">AI analysis report pending — scheduled at 7am daily</p>
              </div>
            )}

            {api.data.score_breakdown && (
              <div className="p-5 border-t border-emerald-200 dark:border-emerald-800">
                <h3 className="text-xs font-semibold text-emerald-700 dark:text-emerald-400 uppercase tracking-wide mb-2">
                  Factor Score Breakdown
                  <span className="text-[10px] text-gray-400 ml-2 font-normal normal-case">Source: Quarterly financials</span>
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                  {Object.entries(api.data.score_breakdown).map(([factor, b]: [string, any]) => (
                    <div key={factor} className="flex items-center justify-between text-xs bg-white/70 dark:bg-gray-800/60 rounded px-3 py-2 min-h-[40px] border border-gray-100 dark:border-gray-700/50">
                      <span className="text-gray-600 dark:text-gray-400 capitalize truncate mr-2">{factor.replace(/_/g, ' ')}</span>
                      <span className="font-mono text-gray-800 dark:text-gray-200 flex-shrink-0 tabular-nums">{b.weighted?.toFixed(1) || '—'}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* 30-Day Price Trend */}
        <div className="mb-6">
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
            <div className="w-full">
              <SparklineChart data={displayStock.sparkline} height={80} />
            </div>
          </div>
        </div>

        {/* Quarterly Financials */}
        <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-800 mb-6">
          <h2 className="font-semibold text-sm text-gray-700 dark:text-gray-300 mb-3">Quarterly Financials</h2>
          {displayStock.financials.length === 0 ? (
            <p className="text-xs text-gray-400 py-4">Financial data will appear after the next pipeline run.</p>
          ) : (
            <div className="overflow-x-auto -mx-4 px-4 sm:mx-0 sm:px-0" style={{ WebkitOverflowScrolling: 'touch' }}>
              <table className="w-full text-xs whitespace-nowrap sm:whitespace-normal">
                <thead>
                  <tr className="text-gray-500 border-b border-gray-200 dark:border-gray-700">
                    <th className="text-left py-2 pr-4 sticky left-0 bg-white dark:bg-gray-950 z-10">Quarter</th>
                    <th className="text-right py-2 px-2">Revenue <span className="hidden sm:inline">(RM)</span></th>
                    <th className="text-right py-2 px-2">Net Income</th>
                    <th className="text-right py-2 px-2 hidden sm:table-cell">FCF</th>
                    <th className="text-right py-2 px-2 hidden sm:table-cell">P/E</th>
                    <th className="text-right py-2 px-2 hidden sm:table-cell">ROE</th>
                    <th className="text-right py-2 px-2 hidden sm:table-cell">D/E</th>
                    <th className="text-right py-2 px-2">Rev Growth</th>
                  </tr>
                </thead>
                <tbody>
                  {displayStock.financials.map((f, idx) => (
                    <tr key={f.quarter} className={`border-b border-gray-100 dark:border-gray-800 ${idx % 2 === 0 ? 'bg-gray-50/50 dark:bg-gray-900/30' : ''}`}>
                      <td className={`py-2 pr-4 font-medium text-gray-700 dark:text-gray-300 sticky left-0 z-10 ${idx % 2 === 0 ? 'bg-gray-50/50 dark:bg-gray-900/30' : 'bg-white dark:bg-gray-950'}`}>
                        {f.quarter}
                      </td>
                      <td className="text-right py-2 px-2 font-mono">{f.revenue >= 1_000_000 ? `${(f.revenue / 1_000_000).toFixed(1)}M` : f.revenue >= 1_000 ? `${(f.revenue / 1_000).toFixed(1)}K` : f.revenue.toLocaleString()}</td>
                      <td className="text-right py-2 px-2 font-mono">{f.netIncome >= 1_000_000 ? `${(f.netIncome / 1_000_000).toFixed(1)}M` : f.netIncome >= 1_000 ? `${(f.netIncome / 1_000).toFixed(1)}K` : f.netIncome.toLocaleString()}</td>
                      <td className="text-right py-2 px-2 font-mono hidden sm:table-cell">{f.freeCashFlow >= 1_000_000 ? `${(f.freeCashFlow / 1_000_000).toFixed(1)}M` : f.freeCashFlow >= 1_000 ? `${(f.freeCashFlow / 1_000).toFixed(1)}K` : f.freeCashFlow.toLocaleString()}</td>
                      <td className="text-right py-2 px-2 font-mono hidden sm:table-cell">{f.peRatio.toFixed(1)}</td>
                      <td className="text-right py-2 px-2 font-mono hidden sm:table-cell">{f.roe.toFixed(1)}%</td>
                      <td className="text-right py-2 px-2 font-mono hidden sm:table-cell">{f.debtToEquity.toFixed(1)}</td>
                      <td className={`text-right py-2 px-2 font-mono ${f.revenueGrowthYoY >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-500 dark:text-red-400'}`}>
                        {f.revenueGrowthYoY >= 0 ? '+' : ''}{f.revenueGrowthYoY.toFixed(1)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="text-[10px] text-gray-400 mt-2 sm:hidden">P/E, ROE, D/E, FCF columns hidden on mobile. Rotate to landscape or view on tablet+.</p>
            </div>
          )}
        </div>

        {/* Dividend History */}
        <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-800 mb-6">
          <h2 className="font-semibold text-sm text-gray-700 dark:text-gray-300 mb-3">Dividend History</h2>
          {divData.length === 0 ? (
            <p className="text-xs text-gray-400 dark:text-gray-500 py-4">Dividend data will appear after the next pipeline run.</p>
          ) : (
            <div className="w-full">
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={divData}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-gray-200 dark:stroke-gray-700" />
                  <XAxis dataKey="date" tick={{ fontSize: 11 }} className="text-gray-500" />
                  <YAxis tick={{ fontSize: 11 }} className="text-gray-500" />
                  <Tooltip contentStyle={{ backgroundColor: 'var(--tooltip-bg, #fff)', border: '1px solid var(--tooltip-border, #e5e7eb)', borderRadius: '8px', fontSize: '12px', color: 'var(--tooltip-color, inherit)' }} />
                  <Bar dataKey="amount" fill="#059669" radius={[4, 4, 0, 0]} name="DPS (RM)" />
                </BarChart>
              </ResponsiveContainer>
            </div>
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
        <div className={`h-4 w-24 mb-4 ${shimmer}`} />
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 md:gap-4 mb-4 md:mb-6">
          <div>
            <div className="flex flex-wrap items-center gap-1.5 md:gap-3 mb-1">
              <div className={`h-7 md:h-8 w-48 ${shimmer}`} />
              <div className={`h-5 w-20 rounded-full ${shimmer}`} />
            </div>
            <div className={`h-3 md:h-4 w-40 mt-1 ${shimmer}`} />
          </div>
          <div className="flex items-center gap-3 md:gap-4 self-start">
            <div className="text-right">
              <div className={`h-8 md:h-9 w-28 mb-1 ${shimmer}`} />
              <div className={`h-4 w-16 ml-auto ${shimmer}`} />
            </div>
            <div className="w-12 h-12 rounded-full bg-gray-200 dark:bg-gray-700 animate-pulse" />
          </div>
        </div>
        <div className="mb-6 rounded-xl border-2 border-emerald-500/20 bg-emerald-50/30 dark:bg-emerald-950/10 overflow-hidden">
          <div className="p-5">
            <div className="flex items-center gap-2">
              <div className={`h-5 w-5 ${shimmer}`} />
              <div className={`h-5 w-32 ${shimmer}`} />
              <div className={`h-5 w-16 rounded-full ${shimmer}`} />
            </div>
          </div>
          <div className="p-5 space-y-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i}><div className={`h-4 w-32 mb-1 ${shimmer}`} /><div className={`h-4 w-full ${shimmer}`} /></div>
            ))}
          </div>
        </div>
        {/* 30-Day Price Trend skeleton */}
        <div className="mb-6">
          <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-800">
            <div className={`h-5 w-32 mb-3 ${shimmer}`} />
            <div className={`h-[80px] w-full ${shimmer}`} />
          </div>
        </div>

        {/* Quarterly Financials skeleton */}
        <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-800 mb-6">
          <div className={`h-5 w-36 mb-3 ${shimmer}`} />
          <div className={`h-4 w-full mb-2 ${shimmer}`} />
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="flex gap-3 mb-2">
              <div className={`h-4 w-24 ${shimmer}`} />
              <div className={`h-4 w-16 ${shimmer}`} />
              <div className={`h-4 w-16 ${shimmer}`} />
            </div>
          ))}
        </div>

        {/* Dividend History skeleton */}
        <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-800 mb-6">
          <div className={`h-5 w-32 mb-3 ${shimmer}`} />
          <div className={`h-[200px] w-full ${shimmer}`} />
        </div>
      </main>
    </div>
  )
}
