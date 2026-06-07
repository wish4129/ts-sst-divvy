/**
 * Cron Status Lambda — returns status of all Divvy cron jobs.
 *
 * Reads from the local Hermes cron jobs.json (available in dev/local SST).
 * In production Lambda, falls back to returning job definitions without live status.
 */
import fs from 'fs'
import path from 'path'

// All 8 Divvy cron jobs with their known IDs and schedules
const DIVVY_JOBS = [
  { id: '26953f8d3292', name: 'Portfolio Battle', schedule: '0,30 9-17 * * 3-5', description: 'Wed-Fri 30min: portfolio_manager.py → DB' },
  { id: 'ef7f9d4ea5ae', name: 'Score Alert', schedule: '0 9 * * *', description: 'Daily 9am: industry_scorer.py → status align → Kronos warnings' },
  { id: '4fc209772753', name: 'KLSE Screener', schedule: '0 9 * * 1', description: 'Mon 9am: scrape KLSE → insert candidates → Kronos' },
  { id: '557f80fbdeb8', name: 'Deep Dive', schedule: '0 10 * * 1', description: 'Mon 10am: Kronos → analyze → AI reports → rebalance' },
  { id: '6a61d251c37a', name: 'Random Deep Analysis', schedule: '0 14 * * 1-5', description: 'Weekdays 2pm: --count 3 random analysis → DB' },
  { id: 'ccd74009601b', name: 'Process Pending', schedule: '0,30 9-17 * * 1-5', description: '30min trading hrs: --pending queue → DB' },
  { id: 'e01059a70366', name: 'Improvement Agent', schedule: 'every 60m', description: 'Claims next ready kanban task, implements via opencode' },
  { id: '6a996a29e345', name: 'Plan Refresher', schedule: 'every 240m', description: 'Reviews board progress, marks completed, adds tasks' },
]

interface CronJobStatus {
  id: string
  name: string
  schedule: string
  description: string
  lastRun: string | null
  status: 'ok' | 'error' | 'unknown' | 'never'
  error: string | null
  enabled: boolean
}

function tryReadLocalCron(): Record<string, { lastRun: string; status: string; error: string; enabled: boolean }> | null {
  try {
    // Local cron jobs.json path (Kevin's machine only)
    const homePath = process.env.HOME || '/Users/munkevin'
    const jobsPath = path.join(homePath, '.hermes', 'cron', 'jobs.json')
    if (!fs.existsSync(jobsPath)) return null
    const raw = fs.readFileSync(jobsPath, 'utf-8')
    const data = JSON.parse(raw)
    const jobs: any[] = data.jobs || []
    const result: Record<string, any> = {}
    for (const j of jobs) {
      result[j.id] = {
        lastRun: j.last_run_at || null,
        status: j.last_status || 'unknown',
        error: j.last_error || null,
        enabled: j.enabled !== false,
      }
    }
    return result
  } catch {
    return null
  }
}

export async function handler(): Promise<{statusCode: number; body: string; headers: Record<string,string>}> {
  const liveData = tryReadLocalCron()

  const jobs: CronJobStatus[] = DIVVY_JOBS.map(def => {
    const live = liveData?.[def.id]
    return {
      id: def.id,
      name: def.name,
      schedule: def.schedule,
      description: def.description,
      lastRun: live?.lastRun || null,
      status: (live?.status || 'unknown') as CronJobStatus['status'],
      error: live?.error || null,
      enabled: live?.enabled ?? true,
    }
  })

  return {
    statusCode: 200,
    body: JSON.stringify({
      jobs,
      source: liveData ? 'local' : 'static',
      updatedAt: new Date().toISOString(),
    }),
    headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
  }
}
