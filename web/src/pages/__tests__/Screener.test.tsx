import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import Screener from '../Screener'

const { mockUseApi } = vi.hoisted(() => ({ mockUseApi: vi.fn() }))
vi.mock('../../hooks/useApi', () => ({ useApi: mockUseApi }))

describe('Screener page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders page title', () => {
    mockUseApi.mockReturnValue({ data: [], loading: false, error: null, refetch: vi.fn() })
    render(<MemoryRouter><Screener /></MemoryRouter>)
    expect(screen.getByText(/stock screener/i)).toBeTruthy()
  })

  it('shows skeleton during loading', () => {
    mockUseApi.mockReturnValue({ data: null, loading: true, error: null, refetch: vi.fn() })
    render(<MemoryRouter><Screener /></MemoryRouter>)
    // Loading state still shows "Stock Screener" title + skeleton divs
    expect(screen.getByText(/stock screener/i)).toBeTruthy()
    const skeletons = document.querySelectorAll('.animate-pulse')
    expect(skeletons.length).toBeGreaterThan(0)
  })

  it('shows empty state when no candidates', () => {
    mockUseApi.mockReturnValue({ data: [], loading: false, error: null, refetch: vi.fn() })
    render(<MemoryRouter><Screener /></MemoryRouter>)
    expect(screen.getByText(/no screener candidates yet/i)).toBeTruthy()
  })

  it('renders candidate list when data loaded', () => {
    mockUseApi.mockReturnValue({
      data: [
        { id: 1, stockCode: '1155', stockName: 'Maybank', peRatio: 12.5, dividendYield: 5.2, roe: 10.1, compositeScore: 82, scannedAt: '2025-01-01', inWatchlist: false },
        { id: 2, stockCode: '1295', stockName: 'Public Bank', peRatio: 11.2, dividendYield: 4.8, roe: 12.3, compositeScore: 78, scannedAt: '2025-01-01', inWatchlist: true },
      ],
      loading: false, error: null, refetch: vi.fn(),
    })
    render(<MemoryRouter><Screener /></MemoryRouter>)
    expect(screen.getByText(/Maybank/i)).toBeTruthy()
    expect(screen.getByText(/Public Bank/i)).toBeTruthy()
  })

  it('shows search input when candidates exist', () => {
    mockUseApi.mockReturnValue({
      data: [
        { id: 1, stockCode: '1155', stockName: 'Maybank', peRatio: 12.5, dividendYield: 5.2, roe: 10.1, compositeScore: 82, scannedAt: '2025-01-01', inWatchlist: false },
      ],
      loading: false, error: null, refetch: vi.fn(),
    })
    render(<MemoryRouter><Screener /></MemoryRouter>)
    const input = screen.getByPlaceholderText(/search stocks/i)
    expect(input).toBeTruthy()
  })

  it('displays scores on candidates', () => {
    mockUseApi.mockReturnValue({
      data: [
        { id: 1, stockCode: '1155', stockName: 'Maybank', peRatio: 12.5, dividendYield: 5.2, roe: 10.1, compositeScore: 82, scannedAt: '2025-01-01', inWatchlist: false },
      ],
      loading: false, error: null, refetch: vi.fn(),
    })
    render(<MemoryRouter><Screener /></MemoryRouter>)
    expect(screen.getByText('82')).toBeTruthy()
  })

  it('shows error state', () => {
    mockUseApi.mockReturnValue({ data: null, loading: false, error: 'Network error', refetch: vi.fn() })
    render(<MemoryRouter><Screener /></MemoryRouter>)
    expect(screen.getByText(/failed to load screener/i)).toBeTruthy()
  })
})
