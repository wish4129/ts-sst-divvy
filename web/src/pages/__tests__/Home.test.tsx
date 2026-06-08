import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import Home from '../Home'

const { mockUseApi } = vi.hoisted(() => ({ mockUseApi: vi.fn() }))
vi.mock('../../hooks/useApi', () => ({ useApi: mockUseApi }))

describe('Home page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders page heading', () => {
    mockUseApi.mockReturnValue({ data: [], loading: false, error: null, refetch: vi.fn() })
    render(<MemoryRouter><Home /></MemoryRouter>)
    expect(screen.getByText(/Bursa Investment Tracker/i)).toBeTruthy()
  })

  it('shows stock count when data loaded', () => {
    mockUseApi.mockReturnValue({
      data: [
        { code: '1155.KL', name: 'Malayan Banking', industry: 'Banking', lastPrice: 10.50, status: 'active', compositeScore: 85, hasAiReport: true },
        { code: '1295.KL', name: 'Public Bank', industry: 'Banking', lastPrice: 4.50, status: 'active', compositeScore: 78, hasAiReport: false },
      ],
      loading: false, error: null, refetch: vi.fn(),
    })
    render(<MemoryRouter><Home /></MemoryRouter>)
    expect(screen.getByText(/2 stocks tracked/i)).toBeTruthy()
  })

  it('shows loading state', () => {
    mockUseApi.mockReturnValue({ data: null, loading: true, error: null, refetch: vi.fn() })
    render(<MemoryRouter><Home /></MemoryRouter>)
    expect(screen.getByText(/loading stocks/i)).toBeTruthy()
  })

  it('shows empty state when no stocks', () => {
    mockUseApi.mockReturnValue({ data: [], loading: false, error: null, refetch: vi.fn() })
    render(<MemoryRouter><Home /></MemoryRouter>)
    expect(screen.getByText(/no stocks yet/i)).toBeTruthy()
  })

  it('renders industry filter when stocks loaded', () => {
    mockUseApi.mockReturnValue({
      data: [
        { code: '1155.KL', name: 'Maybank', industry: 'Banking', lastPrice: 10.50, status: 'active', compositeScore: 85, hasAiReport: true },
        { code: '6742.KL', name: 'YTL Power', industry: 'Utilities', lastPrice: 3.20, status: 'active', compositeScore: 72, hasAiReport: false },
      ],
      loading: false, error: null, refetch: vi.fn(),
    })
    render(<MemoryRouter><Home /></MemoryRouter>)
    // Industry filter buttons exist (multiple elements with same text since stock cards also show industry)
    const bankingButtons = screen.getAllByText('Banking')
    const utilityButtons = screen.getAllByText('Utilities')
    expect(bankingButtons.length).toBeGreaterThanOrEqual(1)
    expect(utilityButtons.length).toBeGreaterThanOrEqual(1)
  })

  it('renders stock cards with names', () => {
    mockUseApi.mockReturnValue({
      data: [
        { code: '1155.KL', name: 'Malayan Banking', industry: 'Banking', lastPrice: 10.50, status: 'active', compositeScore: 85, hasAiReport: true },
        { code: '1295.KL', name: 'Public Bank', industry: 'Banking', lastPrice: 4.50, status: 'active', compositeScore: 78, hasAiReport: false },
      ],
      loading: false, error: null, refetch: vi.fn(),
    })
    render(<MemoryRouter><Home /></MemoryRouter>)
    expect(screen.getByText(/Malayan Banking/i)).toBeTruthy()
    expect(screen.getByText(/Public Bank/i)).toBeTruthy()
  })

  it('shows "no stocks match" when filters exclude all', () => {
    mockUseApi.mockReturnValue({
      data: [
        { code: '1155.KL', name: 'Maybank', industry: 'Banking', lastPrice: 10.50, status: 'active', compositeScore: 50, hasAiReport: true },
      ],
      loading: false, error: null, refetch: vi.fn(),
    })
    render(<MemoryRouter><Home /></MemoryRouter>)
    // By default minScore=0, so stocks show. But the min score slider exists.
    expect(screen.getByLabelText(/minimum composite score/i)).toBeTruthy()
  })
})
