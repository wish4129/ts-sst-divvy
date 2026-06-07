import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import DividendCalendar from '../DividendCalendar'

const { mockUseApi } = vi.hoisted(() => ({ mockUseApi: vi.fn() }))
vi.mock('../../hooks/useApi', () => ({ useApi: mockUseApi }))

describe('DividendCalendar page', () => {
  it('renders page title', () => {
    mockUseApi.mockReturnValue({ data: [], loading: false, error: null, refetch: vi.fn() })
    render(<MemoryRouter><DividendCalendar /></MemoryRouter>)
    expect(screen.getByText(/dividend calendar/i)).toBeTruthy()
  })

  it('shows skeleton during loading', () => {
    mockUseApi.mockReturnValue({ data: null, loading: true, error: null, refetch: vi.fn() })
    render(<MemoryRouter><DividendCalendar /></MemoryRouter>)
    // Loading shows title + skeleton
    expect(screen.getByText(/dividend calendar/i)).toBeTruthy()
    const skeletons = document.querySelectorAll('.animate-pulse')
    expect(skeletons.length).toBeGreaterThan(0)
  })

  it('shows month navigation', () => {
    mockUseApi.mockReturnValue({ data: [], loading: false, error: null, refetch: vi.fn() })
    render(<MemoryRouter><DividendCalendar /></MemoryRouter>)
    expect(screen.getByLabelText(/previous month/i)).toBeTruthy()
    expect(screen.getByLabelText(/next month/i)).toBeTruthy()
  })

  it('shows empty state when no dividend data', () => {
    mockUseApi.mockReturnValue({ data: [], loading: false, error: null, refetch: vi.fn() })
    render(<MemoryRouter><DividendCalendar /></MemoryRouter>)
    expect(screen.getByText(/no dividend data yet/i)).toBeTruthy()
  })

  it('shows summary cards with data counts', () => {
    mockUseApi.mockReturnValue({
      data: [
        { code: '1155.KL', name: 'Maybank', industry: 'Banking', lastPrice: 10.50, status: 'active', compositeScore: 85, hasAiReport: true },
      ],
      loading: false, error: null, refetch: vi.fn(),
    })
    render(<MemoryRouter><DividendCalendar /></MemoryRouter>)
    expect(screen.getByText(/stocks with yield/i)).toBeTruthy()
    expect(screen.getByText(/avg dividend yield/i)).toBeTruthy()
  })

  it('shows current month in navigation', () => {
    mockUseApi.mockReturnValue({ data: [], loading: false, error: null, refetch: vi.fn() })
    render(<MemoryRouter><DividendCalendar /></MemoryRouter>)
    const now = new Date()
    const monthName = now.toLocaleString('default', { month: 'long' })
    expect(screen.getByText(new RegExp(monthName, 'i'))).toBeTruthy()
  })
})
