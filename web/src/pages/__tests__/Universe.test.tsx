import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import Universe from '../Universe'

const { mockUseApi } = vi.hoisted(() => ({ mockUseApi: vi.fn() }))
vi.mock('../../hooks/useApi', () => ({ useApi: mockUseApi }))

describe('Universe page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders page title', () => {
    mockUseApi.mockReturnValue({ data: { data: [], pagination: { total: 0 } }, loading: false, error: null, refetch: vi.fn() })
    render(<MemoryRouter><Universe /></MemoryRouter>)
    expect(screen.getByText(/Bursa Universe/i)).toBeTruthy()
  })

  it('shows loading spinner', () => {
    mockUseApi.mockReturnValue({ data: null, loading: true, error: null, refetch: vi.fn() })
    render(<MemoryRouter><Universe /></MemoryRouter>)
    // The loading state has a Loader2 spinner, don't look for text "loading"
    expect(screen.getByRole('status')).toBeTruthy()
  })

  it('renders stock list when data loaded', () => {
    mockUseApi.mockReturnValue({
      data: {
        data: [
          { stock_code: '1155.KL', name: 'Malayan Banking', industry: 'Banking', last_price: 10.50, has_analysis: true, last_analyzed_at: null, market_cap: null, pe_ratio: null, dividend_yield: null, added_at: '2024-01-01' },
          { stock_code: '1295.KL', name: 'Public Bank', industry: 'Banking', last_price: 4.50, has_analysis: false, last_analyzed_at: null, market_cap: null, pe_ratio: null, dividend_yield: null, added_at: '2024-01-01' },
        ],
        pagination: { total: 2 },
      },
      loading: false, error: null, refetch: vi.fn(),
    })
    render(<MemoryRouter><Universe /></MemoryRouter>)
    expect(screen.getByText(/Malayan Banking/i)).toBeTruthy()
    expect(screen.getByText(/Public Bank/i)).toBeTruthy()
  })

  it('shows search input', () => {
    mockUseApi.mockReturnValue({ data: { data: [], pagination: { total: 0 } }, loading: false, error: null, refetch: vi.fn() })
    render(<MemoryRouter><Universe /></MemoryRouter>)
    const input = screen.getByPlaceholderText(/search/i)
    expect(input).toBeTruthy()
  })

  it('shows empty table when no results', () => {
    mockUseApi.mockReturnValue({ data: { data: [], pagination: { total: 0 } }, loading: false, error: null, refetch: vi.fn() })
    render(<MemoryRouter><Universe /></MemoryRouter>)
    // Table is still rendered, just with 0 rows. Shows "0 stocks · Request deep analysis..."
    expect(screen.getByText(/0 stocks/i)).toBeTruthy()
  })

  it('shows total count', () => {
    mockUseApi.mockReturnValue({
      data: {
        data: [
          { stock_code: '1155.KL', name: 'Maybank', industry: 'Banking', last_price: 10.50, has_analysis: true, last_analyzed_at: null, market_cap: null, pe_ratio: null, dividend_yield: null, added_at: '2024-01-01' },
        ],
        pagination: { total: 798 },
      },
      loading: false, error: null, refetch: vi.fn(),
    })
    render(<MemoryRouter><Universe /></MemoryRouter>)
    expect(screen.getByText(/798 stocks/i)).toBeTruthy()
  })
})
