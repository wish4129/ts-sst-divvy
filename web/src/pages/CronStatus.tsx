import { useState, useEffect, Fragment } from 'react'
import { Helmet } from 'react-helmet-async'
import { Clock, CheckCircle2, XCircle, AlertTriangle, RefreshCw } from 'lucide-react'

interface CronJob {
  id: string
  name: string
  schedule: string
  description: string
  lastRun: string | null
  status: 'ok' | 'error' | 'unknown' | 'never'
  error: string | null
  enabled: boolean
}

const STATUS_ICON: Record<string, { icon: typeof CheckCircle2; color: string; label: string }> = {
  ok: { icon: CheckCircle2, color: 'text-emerald-500', label: 'OK' },
  error: { icon: XCircle, color: 'text-red-500', label: 'Error' },
  unknown: { icon: AlertTriangle, color: 'text-amber-500', label: 'Unknown' },
  never: { icon: Clock, color: 'text-slate-400', label: 'Never run' },
}

function relativeTime(iso: string | null): string {
  if (!iso) return 'Never'
  try {
    const diff = Date.now() - new Date(iso).getTime()
    const mins = Math.floor(diff / 60000)
    if (mins < 1) return 'Just now'
    if (mins < 60) return `${mins}m ago`
    const hours = Math.floor(mins / 60)
    if (hours < 24) return `${hours}h ago`
    const days = Math.floor(hours / 24)
    return `${days}d ago`
  } catch {
    return 'Unknown'
  }
}

export default function CronStatus() {
  const [jobs, setJobs] = useState<CronJob[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [source, setSource] = useState<string>('')

  const fetchStatus = () => {
    setLoading(true)
    const apiUrl = import.meta.env.VITE_API_URL || ''
    fetch(`${apiUrl}/cron/status`)
      .then(r => r.json())
      .then(data => {
        setJobs(data.jobs || [])
        setSource(data.source || '')
        setError(null)
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    fetchStatus()
    const interval = setInterval(fetchStatus, 60000)
    return () => clearInterval(interval)
  }, [])

  const okCount = jobs.filter(j => j.status === 'ok').length
  const errCount = jobs.filter(j => j.status === 'error').length

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <Helmet>
        <title>Cron Status — Divvy Bursa Tracker</title>
        <meta name="description" content="Divvy cron job status dashboard. Monitor pipeline health, last run times, and error tracking." />
        <meta name="robots" content="noindex" />
      </Helmet>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Cron Health</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            {loading ? 'Loading...' : `${jobs.length} jobs · ${okCount} OK · ${errCount} errors`}
            {source === 'local' && ' · live data'}
            {source === 'static' && ' · static definitions (no live data in production)'}
          </p>
        </div>
        <button
          onClick={fetchStatus}
          className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          title="Refresh"
        >
          <RefreshCw className={`w-5 h-5 text-gray-500 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-400 text-sm">
          Failed to load: {error}
        </div>
      )}

      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/50">
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">Job</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase hidden sm:table-cell">Schedule</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">Last Run</th>
                <th className="text-center px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase w-20">Status</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map(job => {
                const statusInfo = STATUS_ICON[job.status] || STATUS_ICON.unknown
                const Icon = statusInfo.icon
                const isExpanded = expandedId === job.id
                return (
                  <Fragment key={job.id}>
                    <tr
                      key={job.id}
                      onClick={() => job.error && setExpandedId(isExpanded ? null : job.id)}
                      className={`border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/30 transition-colors ${job.error ? 'cursor-pointer' : ''}`}
                    >
                      <td className="px-4 py-3">
                        <div className="font-medium text-gray-900 dark:text-white text-sm">{job.name}</div>
                        <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{job.description}</div>
                      </td>
                      <td className="px-4 py-3 hidden sm:table-cell">
                        <code className="text-xs bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded text-gray-600 dark:text-gray-400">
                          {job.schedule}
                        </code>
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-sm text-gray-600 dark:text-gray-400">
                          {relativeTime(job.lastRun)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <div className="flex items-center justify-center gap-1.5">
                          <Icon className={`w-4 h-4 ${statusInfo.color}`} />
                          <span className={`text-xs font-medium ${statusInfo.color}`}>{statusInfo.label}</span>
                        </div>
                      </td>
                    </tr>
                    {isExpanded && job.error && (
                      <tr key={`${job.id}-error`}>
                        <td colSpan={4} className="px-4 py-3 bg-red-50 dark:bg-red-900/10">
                          <pre className="text-xs text-red-700 dark:text-red-400 whitespace-pre-wrap font-mono">
                            {job.error}
                          </pre>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      <p className="text-xs text-gray-400 dark:text-gray-600 mt-4 text-center">
        Auto-refreshes every 60 seconds · {source === 'local' ? 'Reading from local cron database' : 'Live status available in local dev mode only'}
      </p>
    </div>
  )
}
