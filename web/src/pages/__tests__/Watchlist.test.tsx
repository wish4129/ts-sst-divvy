import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import Watchlist from '../Watchlist'

const { mockUseApi } = vi.hoisted(() => ({ mockUseApi: vi.fn() }))
vi.mock('../../hooks/useApi', () => ({ useApi: mockUseApi }))

function mockApiResponse(data: any = null, loading = false, error: string | null = null) {
  mockUseApi.mockReturnValue({ data, loading, error, refetch: vi.fn() })
}

describe('Watchlist page', () => {
  it('renders page title', () => {
    mockApiResponse([])
    render(<MemoryRouter><Watchlist /></MemoryRouter>)
    expect(screen.getByText('Watchlist')).toBeTruthy()
  })

  it('renders tab buttons', () => {
    mockApiResponse([])
    render(<MemoryRouter><Watchlist /></MemoryRouter>)
    expect(screen.getByText(/Active/)).toBeTruthy()
    expect(screen.getByText(/Revisit/)).toBeTruthy()
    expect(screen.getByText(/Removed/)).toBeTruthy()
  })

  it('shows loading skeleton', () => {
    mockApiResponse(null, true)
    render(<MemoryRouter><Watchlist /></MemoryRouter>)
    const skeletons = document.querySelectorAll('.animate-pulse')
    expect(skeletons.length).toBeGreaterThan(0)
  })

  it('shows empty state when no stocks', () => {
    mockApiResponse([])
    render(<MemoryRouter><Watchlist /></MemoryRouter>)
    expect(screen.getByText(/no active stocks yet/i)).toBeTruthy()
  })

  it('renders stock names from API data', () => {
    mockApiResponse([
      { code: '1155.KL', name: 'Malayan Banking', industry: 'Banking', lastPrice: 10.50, status: 'active', compositeScore: 85, hasAiReport: true },
      { code: '1295.KL', name: 'Public Bank', industry: 'Banking', lastPrice: 4.50, status: 'active', compositeScore: 78, hasAiReport: false },
    ])
    render(<MemoryRouter><Watchlist /></MemoryRouter>)
    expect(screen.getByText(/Malayan Banking/i)).toBeTruthy()
    expect(screen.getByText(/Public Bank/i)).toBeTruthy()
  })

  it('shows error gracefully (no error UI — shows empty state)', () => {
    mockApiResponse(null, false, 'Failed to load')
    render(<MemoryRouter><Watchlist /></MemoryRouter>)
    expect(screen.getByText('Watchlist')).toBeTruthy()
  })

  it('renders Export CSV button when stocks loaded', () => {
    mockApiResponse([
      { code: '1155.KL', name: 'Maybank', industry: 'Banking', lastPrice: 10.50, status: 'active', compositeScore: 85, hasAiReport: true },
    ])
    render(<MemoryRouter><Watchlist /></MemoryRouter>)
    expect(screen.getByText(/export csv/i)).toBeTruthy()
  })

  it('shows stock scores on cards', () => {
    mockApiResponse([
      { code: '1155.KL', name: 'Maybank', industry: 'Banking', lastPrice: 10.50, status: 'active', compositeScore: 85, hasAiReport: true },
      { code: '1295.KL', name: 'PBBANK', industry: 'Banking', lastPrice: 4.50, status: 'active', compositeScore: 75, hasAiReport: false },
    ])
    render(<MemoryRouter><Watchlist /></MemoryRouter>)
    // Both stocks have score ≥ 70, so both appear on Active tab
    expect(screen.getAllByText('85').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('75').length).toBeGreaterThanOrEqual(1)
  })

  it('switches to Revisit tab and shows low-score stocks', () => {
    mockApiResponse([
      { code: '1155.KL', name: 'Maybank', industry: 'Banking', lastPrice: 10.50, status: 'active', compositeScore: 85, hasAiReport: true },
      { code: '1295.KL', name: 'PBBANK', industry: 'Banking', lastPrice: 4.50, status: 'active', compositeScore: 55, hasAiReport: false },
    ])
    render(<MemoryRouter><Watchlist /></MemoryRouter>)
    // Active tab shows Maybank (score 85 ≥ 70) — name + short code both match /Maybank/i
    expect(screen.getAllByText(/Maybank/i).length).toBeGreaterThanOrEqual(1)
    // Click Revisit tab
    fireEvent.click(screen.getByText(/Revisit/))
    // PBBANK with score 55 (< 70) should appear in Revisit tab
    expect(screen.getByText('PBBANK')).toBeTruthy()
  })
})
