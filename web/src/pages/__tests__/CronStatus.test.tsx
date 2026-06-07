import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import CronStatus from '../CronStatus'

// Mock global fetch
const mockFetch = vi.fn()
global.fetch = mockFetch

// Mock setInterval/clearInterval to capture callbacks
let intervalCallback: (() => void) | null = null
let clearIntervalCalled = false
const originalSetInterval = global.setInterval
const originalClearInterval = global.clearInterval

function mockFetchResponse(data: any) {
  mockFetch.mockResolvedValueOnce({
    ok: true,
    json: () => Promise.resolve(data),
  })
}

function mockFetchError(message: string) {
  mockFetch.mockRejectedValueOnce(new Error(message))
}

describe('CronStatus page', () => {
  beforeEach(() => {
    mockFetch.mockReset()
    intervalCallback = null
    clearIntervalCalled = false
    // Mock setInterval to capture callback and return a fake ID
    vi.spyOn(global, 'setInterval').mockImplementation((cb: () => void, _ms: number) => {
      intervalCallback = cb
      return 123 as unknown as ReturnType<typeof setInterval>
    })
    vi.spyOn(global, 'clearInterval').mockImplementation(() => {
      clearIntervalCalled = true
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders page title', async () => {
    mockFetchResponse({ jobs: [], source: 'static' })
    render(<CronStatus />)
    await waitFor(() => expect(screen.getByText('Cron Health')).toBeTruthy())
  })

  it('shows loading text before fetch resolves', () => {
    // Return a promise that won't resolve during this test
    mockFetch.mockReturnValue(new Promise(() => {}))
    render(<CronStatus />)
    expect(screen.getByText('Loading...')).toBeTruthy()
  })

  it('renders all 8 cron jobs with names', async () => {
    mockFetchResponse({
      jobs: [
        { id: 'a', name: 'Portfolio Battle', schedule: '0,30 9-17 * * 3-5', description: 'Wed-Fri 30min', lastRun: null, status: 'unknown', error: null, enabled: true },
        { id: 'b', name: 'Score Alert', schedule: '0 9 * * *', description: 'Daily 9am', lastRun: null, status: 'unknown', error: null, enabled: true },
        { id: 'c', name: 'KLSE Screener', schedule: '0 9 * * 1', description: 'Mon 9am', lastRun: null, status: 'unknown', error: null, enabled: true },
        { id: 'd', name: 'Deep Dive', schedule: '0 10 * * 1', description: 'Mon 10am', lastRun: null, status: 'unknown', error: null, enabled: true },
        { id: 'e', name: 'Random Deep Analysis', schedule: '0 14 * * 1-5', description: 'Weekdays 2pm', lastRun: null, status: 'unknown', error: null, enabled: true },
        { id: 'f', name: 'Process Pending', schedule: '0,30 9-17 * * 1-5', description: '30min trading hrs', lastRun: null, status: 'unknown', error: null, enabled: true },
        { id: 'g', name: 'Improvement Agent', schedule: 'every 60m', description: 'Claims kanban tasks', lastRun: null, status: 'unknown', error: null, enabled: true },
        { id: 'h', name: 'Plan Refresher', schedule: 'every 240m', description: 'Reviews board', lastRun: null, status: 'unknown', error: null, enabled: true },
      ],
      source: 'static',
    })
    render(<CronStatus />)

    await waitFor(() => {
      expect(screen.getByText('Portfolio Battle')).toBeTruthy()
      expect(screen.getByText('Score Alert')).toBeTruthy()
      expect(screen.getByText('KLSE Screener')).toBeTruthy()
      expect(screen.getByText('Deep Dive')).toBeTruthy()
      expect(screen.getByText('Random Deep Analysis')).toBeTruthy()
      expect(screen.getByText('Process Pending')).toBeTruthy()
      expect(screen.getByText('Improvement Agent')).toBeTruthy()
      expect(screen.getByText('Plan Refresher')).toBeTruthy()
    })
  })

  it('shows job count summary', async () => {
    mockFetchResponse({
      jobs: [
        { id: 'a', name: 'Job 1', schedule: '* * * * *', description: 'desc', lastRun: null, status: 'ok', error: null, enabled: true },
        { id: 'b', name: 'Job 2', schedule: '* * * * *', description: 'desc', lastRun: null, status: 'error', error: 'Failed', enabled: true },
        { id: 'c', name: 'Job 3', schedule: '* * * * *', description: 'desc', lastRun: null, status: 'unknown', error: null, enabled: true },
      ],
      source: 'static',
    })
    render(<CronStatus />)

    await waitFor(() => {
      expect(screen.getByText(/3 jobs/)).toBeTruthy()
      expect(screen.getByText(/1 OK/)).toBeTruthy()
      expect(screen.getByText(/1 errors/)).toBeTruthy()
    })
  })

  it('shows empty state when no jobs', async () => {
    mockFetchResponse({ jobs: [], source: 'static' })
    render(<CronStatus />)

    await waitFor(() => {
      expect(screen.getByText(/0 jobs/)).toBeTruthy()
      expect(screen.getByText(/0 OK/)).toBeTruthy()
      expect(screen.getByText(/0 errors/)).toBeTruthy()
    })
  })

  it('renders status badges with correct labels', async () => {
    mockFetchResponse({
      jobs: [
        { id: 'a', name: 'OK Job', schedule: '* * * * *', description: 'desc', lastRun: null, status: 'ok', error: null, enabled: true },
        { id: 'b', name: 'Error Job', schedule: '* * * * *', description: 'desc', lastRun: null, status: 'error', error: 'Failed', enabled: true },
        { id: 'c', name: 'Unknown Job', schedule: '* * * * *', description: 'desc', lastRun: null, status: 'unknown', error: null, enabled: true },
        { id: 'd', name: 'Never Job', schedule: '* * * * *', description: 'desc', lastRun: null, status: 'never', error: null, enabled: true },
      ],
      source: 'static',
    })
    render(<CronStatus />)

    await waitFor(() => {
      expect(screen.getByText('OK')).toBeTruthy()
      expect(screen.getByText('Error')).toBeTruthy()
      expect(screen.getByText('Unknown')).toBeTruthy()
      expect(screen.getByText('Never run')).toBeTruthy()
    })
  })

  it('shows relative timestamps for lastRun', async () => {
    // Mock Date.now to return a fixed timestamp
    const nowSpy = vi.spyOn(Date, 'now').mockReturnValue(new Date('2026-06-07T10:00:00Z').getTime())

    mockFetchResponse({
      jobs: [
        { id: 'a', name: 'Recent Job', schedule: '* * * * *', description: 'desc', lastRun: '2026-06-07T09:50:00Z', status: 'ok', error: null, enabled: true },
        { id: 'b', name: 'Old Job', schedule: '* * * * *', description: 'desc', lastRun: '2026-06-07T07:00:00Z', status: 'ok', error: null, enabled: true },
        { id: 'c', name: 'Ancient Job', schedule: '* * * * *', description: 'desc', lastRun: '2026-06-06T10:00:00Z', status: 'ok', error: null, enabled: true },
        { id: 'd', name: 'Never Job', schedule: '* * * * *', description: 'desc', lastRun: null, status: 'never', error: null, enabled: true },
      ],
      source: 'static',
    })
    render(<CronStatus />)

    await waitFor(() => {
      expect(screen.getByText('10m ago')).toBeTruthy()
      expect(screen.getByText('3h ago')).toBeTruthy()
      expect(screen.getByText('1d ago')).toBeTruthy()
      expect(screen.getByText('Never')).toBeTruthy()
    })

    nowSpy.mockRestore()
  })

  it('expands error details on click', async () => {
    mockFetchResponse({
      jobs: [
        { id: 'err1', name: 'Failed Job', schedule: '* * * * *', description: 'desc', lastRun: null, status: 'error', error: 'Connection timeout after 30s', enabled: true },
      ],
      source: 'static',
    })
    render(<CronStatus />)

    await waitFor(() => expect(screen.getByText('Failed Job')).toBeTruthy())

    // Error details hidden initially
    expect(screen.queryByText('Connection timeout after 30s')).toBeNull()

    // Click job row to expand
    fireEvent.click(screen.getByText('Failed Job'))

    await waitFor(() => {
      expect(screen.getByText('Connection timeout after 30s')).toBeTruthy()
    })

    // Click again to collapse
    fireEvent.click(screen.getByText('Failed Job'))
    await waitFor(() => {
      expect(screen.queryByText('Connection timeout after 30s')).toBeNull()
    })
  })

  it('does not make rows clickable when no error', async () => {
    mockFetchResponse({
      jobs: [
        { id: 'ok1', name: 'Clean Job', schedule: '* * * * *', description: 'desc', lastRun: null, status: 'ok', error: null, enabled: true },
      ],
      source: 'static',
    })
    render(<CronStatus />)

    await waitFor(() => {
      const row = screen.getByText('Clean Job').closest('tr')
      expect(row?.className).not.toContain('cursor-pointer')
    })
  })

  it('shows static source notice', async () => {
    mockFetchResponse({ jobs: [], source: 'static' })
    render(<CronStatus />)

    await waitFor(() => {
      expect(screen.getByText(/static definitions/)).toBeTruthy()
    })
  })

  it('shows live source notice when local', async () => {
    mockFetchResponse({ jobs: [], source: 'local' })
    render(<CronStatus />)

    await waitFor(() => {
      expect(screen.getByText(/live data/)).toBeTruthy()
    })
  })

  it('shows footer with auto-refresh info', async () => {
    mockFetchResponse({ jobs: [], source: 'static' })
    render(<CronStatus />)

    await waitFor(() => {
      expect(screen.getByText(/Auto-refreshes every 60 seconds/)).toBeTruthy()
    })
  })

  it('shows error banner when fetch fails', async () => {
    mockFetchError('Network error')
    render(<CronStatus />)

    await waitFor(() => {
      expect(screen.getByText(/Failed to load/)).toBeTruthy()
      expect(screen.getByText(/Network error/)).toBeTruthy()
    })
  })

  it('renders refresh button', async () => {
    mockFetchResponse({ jobs: [], source: 'static' })
    render(<CronStatus />)

    await waitFor(() => {
      expect(screen.getByTitle('Refresh')).toBeTruthy()
    })
  })

  it('refetches on refresh button click', async () => {
    mockFetchResponse({ jobs: [], source: 'static' })
    render(<CronStatus />)

    await waitFor(() => {
      expect(screen.getByTitle('Refresh')).toBeTruthy()
    })
    expect(mockFetch).toHaveBeenCalledTimes(1)

    // Setup next response and click refresh
    mockFetchResponse({ jobs: [], source: 'static' })
    fireEvent.click(screen.getByTitle('Refresh'))

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledTimes(2)
    })
  })

  it('shows spinning refresh icon while loading', () => {
    mockFetch.mockReturnValue(new Promise(() => {}))
    render(<CronStatus />)

    const refreshBtn = screen.getByTitle('Refresh')
    const svg = refreshBtn.querySelector('svg')
    expect(svg?.getAttribute('class')).toContain('animate-spin')
  })

  it('handles invalid JSON response gracefully', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.reject(new Error('Invalid JSON')),
    })
    render(<CronStatus />)

    await waitFor(() => {
      expect(screen.getByText(/Failed to load/)).toBeTruthy()
    })
  })

  it('renders schedule codes', async () => {
    mockFetchResponse({
      jobs: [
        { id: 'a', name: 'Job A', schedule: '0,30 9-17 * * 3-5', description: 'desc', lastRun: null, status: 'ok', error: null, enabled: true },
        { id: 'b', name: 'Job B', schedule: 'every 60m', description: 'desc', lastRun: null, status: 'ok', error: null, enabled: true },
      ],
      source: 'static',
    })
    render(<CronStatus />)

    await waitFor(() => {
      expect(screen.getByText('0,30 9-17 * * 3-5')).toBeTruthy()
      expect(screen.getByText('every 60m')).toBeTruthy()
    })
  })

  it('sets up auto-refresh interval on mount', async () => {
    mockFetchResponse({ jobs: [], source: 'static' })
    render(<CronStatus />)

    await waitFor(() => {
      expect(screen.getByText('Cron Health')).toBeTruthy()
    })

    // setInterval was called with 60000ms
    expect(setInterval).toHaveBeenCalledWith(expect.any(Function), 60000)
    expect(intervalCallback).toBeTruthy()
  })

  it('clears interval on unmount', async () => {
    mockFetchResponse({ jobs: [], source: 'static' })
    const { unmount } = render(<CronStatus />)

    await waitFor(() => {
      expect(screen.getByText('Cron Health')).toBeTruthy()
    })

    unmount()
    expect(clearIntervalCalled).toBe(true)
  })
})
