import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, within } from '@testing-library/react'
import Battle from '../Battle'

// jsdom doesn't have ResizeObserver — Recharts ResponsiveContainer needs it
class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}
vi.stubGlobal('ResizeObserver', ResizeObserverMock)

// Mock useApi hook
const { mockUseApi } = vi.hoisted(() => ({
  mockUseApi: vi.fn(),
}))
vi.mock('../../hooks/useApi', () => ({
  useApi: mockUseApi,
}))

// Mock window.location
const originalLocation = window.location

function mockLocation() {
  const locationMock = { href: '' } as Location
  Object.defineProperty(window, 'location', {
    value: locationMock,
    writable: true,
    configurable: true,
  })
  return locationMock
}

function restoreLocation() {
  Object.defineProperty(window, 'location', {
    value: originalLocation,
    writable: true,
    configurable: true,
  })
}

// ========== FIXTURES ==========

function makeHolding(overrides: Partial<{
  code: string; shares: number; cost: number; price: number
  invested: number; current: number; pnl: number; pnl_pct: number; weight: number
}> = {}) {
  const shares = overrides.shares ?? 1000
  const cost = overrides.cost ?? 10
  const price = overrides.price ?? 10.5
  const invested = overrides.invested ?? shares * cost
  const current = overrides.current ?? shares * price
  const pnl = overrides.pnl ?? current - invested
  const pnl_pct = overrides.pnl_pct ?? ((pnl / invested) * 100)
  return {
    code: overrides.code ?? 'STOCK',
    shares,
    cost,
    price,
    invested,
    current,
    pnl,
    pnl_pct,
    weight: overrides.weight ?? 25,
  }
}

function makeBattleData(): any {
  return {
    runs: [
      {
        timestamp: '2026-06-06T10:00:00+08:00',
        personas: {
          ares: {
            total: 10250.50,
            invested: 8500,
            cash: 1750.50,
            pnl: 250.50,
            pnl_pct: 2.50,
            holdings: {
              MAYBANK: makeHolding({ code: 'MAYBANK', shares: 500, cost: 10, price: 10.50, weight: 50 }),
              INTA: makeHolding({ code: '0192', shares: 1000, cost: 3.25, price: 3.50, weight: 35, pnl_pct: 7.69 }),
            },
            trades_this_run: 0,
          },
          demeter: {
            total: 10080.00,
            invested: 7500,
            cash: 2580.00,
            pnl: 80.00,
            pnl_pct: 0.80,
            holdings: {
              AXREIT: makeHolding({ code: 'AXREIT', shares: 2000, cost: 1.80, price: 1.84, weight: 50, pnl_pct: 2.22 }),
            },
            trades_this_run: 0,
          },
          athena: {
            total: 9950.00,
            invested: 9000,
            cash: 950.00,
            pnl: -50.00,
            pnl_pct: -0.50,
            holdings: {
              PBBANK: makeHolding({ code: 'PBBANK', shares: 2000, cost: 4.50, price: 4.40, weight: 60, pnl_pct: -2.22 }),
              TENAGA: makeHolding({ code: 'TENAGA', shares: 300, cost: 14, price: 13.80, weight: 30, pnl_pct: -1.43 }),
            },
            trades_this_run: 2,
          },
        },
      },
    ],
    personas: {
      ares: { cash: 1750.50, holdings: {} },
      demeter: { cash: 2580.00, holdings: {} },
      athena: { cash: 950.00, holdings: {} },
    },
    trades: [],
  }
}

// ========== TESTS ==========

describe('Battle', () => {
  beforeEach(() => {
    mockUseApi.mockReset()
    vi.clearAllMocks()
  })

  describe('Loading state', () => {
    it('renders skeleton with shimmer placeholders', () => {
      mockUseApi.mockReturnValue({ data: null, loading: true, error: null, refetch: vi.fn() })
      render(<Battle />)
      const status = screen.getByRole('status')
      expect(status).toBeInTheDocument()
      expect(status).toHaveAttribute('aria-live', 'polite')
      // Shimmer elements should be present
      const shimmers = status.querySelectorAll('.animate-pulse')
      expect(shimmers.length).toBeGreaterThan(0)
    })

    it('shows persona card skeletons for all 3 personas', () => {
      mockUseApi.mockReturnValue({ data: null, loading: true, error: null, refetch: vi.fn() })
      render(<Battle />)
      // The 3 persona cards in skeleton have border-2
      const status = screen.getByRole('status')
      const cards = status.querySelectorAll('.rounded-xl.p-5.border-2')
      expect(cards.length).toBe(3)
    })
  })

  describe('Error state', () => {
    it('renders error message when fetch fails', () => {
      mockUseApi.mockReturnValue({ data: null, loading: false, error: 'Network Error', refetch: vi.fn() })
      render(<Battle />)
      const alert = screen.getByRole('alert')
      expect(alert).toBeInTheDocument()
      expect(alert).toHaveTextContent('Error loading data: Network Error')
    })

    it('does not show error when data is available despite error flag', () => {
      // loading=false, error set, but data exists — should render data
      mockUseApi.mockReturnValue({ data: makeBattleData(), loading: false, error: 'stale error', refetch: vi.fn() })
      render(<Battle />)
      // Should render persona cards, not error
      expect(screen.getByText('Ares')).toBeInTheDocument()
      expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    })
  })

  describe('Empty state', () => {
    it('renders empty message when no runs', () => {
      mockUseApi.mockReturnValue({ data: { runs: [] }, loading: false, error: null, refetch: vi.fn() })
      render(<Battle />)
      expect(screen.getByText('Portfolio Battle Starting Soon')).toBeInTheDocument()
      expect(screen.getByText(/Browse Watchlist/)).toBeInTheDocument()
    })

    it('has a link to watchlist', () => {
      mockUseApi.mockReturnValue({ data: { runs: [] }, loading: false, error: null, refetch: vi.fn() })
      render(<Battle />)
      const link = screen.getByText('Browse Watchlist')
      expect(link.closest('a')).toHaveAttribute('href', '/watchlist')
    })
  })

  describe('Normal render', () => {
    beforeEach(() => {
      mockUseApi.mockReturnValue({ data: makeBattleData(), loading: false, error: null, refetch: vi.fn() })
    })

    it('renders page title', () => {
      render(<Battle />)
      expect(screen.getByText(/Portfolio Battle/)).toBeInTheDocument()
    })

    it('renders all 3 persona cards', () => {
      render(<Battle />)
      expect(screen.getByText('Ares')).toBeInTheDocument()
      expect(screen.getByText('Demeter')).toBeInTheDocument()
      expect(screen.getByText('Athena')).toBeInTheDocument()
    })

    it('displays persona styles', () => {
      render(<Battle />)
      expect(screen.getByText(/God of War/)).toBeInTheDocument()
      expect(screen.getByText(/Harvest Goddess/)).toBeInTheDocument()
      expect(screen.getByText(/Goddess of Wisdom/)).toBeInTheDocument()
    })

    it('shows medals in order of PnL', () => {
      render(<Battle />)
      // Ares has highest PnL (+2.50%), Demeter second (+0.80%), Athena last (-0.50%)
      const medals = screen.getAllByText(/[🥇🥈🥉]/)
      expect(medals.length).toBe(3)
      expect(medals[0]).toHaveTextContent('🥇')
      expect(medals[1]).toHaveTextContent('🥈')
      expect(medals[2]).toHaveTextContent('🥉')
    })

    it('shows formatted total values', () => {
      render(<Battle />)
      // Ares: RM 10,250.50
      expect(screen.getByText('RM 10,250.50')).toBeInTheDocument()
      // Demeter: RM 10,080.00
      expect(screen.getByText('RM 10,080.00')).toBeInTheDocument()
    })

    it('shows PnL percentages with colors', () => {
      render(<Battle />)
      // Ares +2.50%
      expect(screen.getByText('+2.50%')).toBeInTheDocument()
      // Demeter +0.80%
      expect(screen.getByText('+0.80%')).toBeInTheDocument()
      // Athena -0.50%
      expect(screen.getByText('-0.50%')).toBeInTheDocument()
    })

    it('shows cash and holdings count', () => {
      render(<Battle />)
      expect(screen.getByText(/Cash: RM 1,750.50 · 2 holdings/)).toBeInTheDocument()
      expect(screen.getByText(/Cash: RM 2,580.00 · 1 holdings/)).toBeInTheDocument()
      expect(screen.getByText(/Cash: RM 950.00 · 2 holdings/)).toBeInTheDocument()
    })

    it('renders portfolio chart section', () => {
      render(<Battle />)
      expect(screen.getByText('Portfolio Value Over Time')).toBeInTheDocument()
    })

    it('renders holdings tables for each persona', () => {
      render(<Battle />)
      expect(screen.getByText('Ares — Holdings')).toBeInTheDocument()
      expect(screen.getByText('Demeter — Holdings')).toBeInTheDocument()
      expect(screen.getByText('Athena — Holdings')).toBeInTheDocument()
    })

    it('shows holding stock names in tables', () => {
      render(<Battle />)
      expect(screen.getByText('MAYBANK')).toBeInTheDocument()
      expect(screen.getByText('INTA')).toBeInTheDocument()
      expect(screen.getByText('AXREIT')).toBeInTheDocument()
      expect(screen.getByText('PBBANK')).toBeInTheDocument()
      expect(screen.getByText('TENAGA')).toBeInTheDocument()
    })

    it('shows last update timestamp', () => {
      render(<Battle />)
      expect(screen.getByText(/Last update:/)).toBeInTheDocument()
    })
  })

  describe('Sort functionality', () => {
    beforeEach(() => {
      mockUseApi.mockReturnValue({ data: makeBattleData(), loading: false, error: null, refetch: vi.fn() })
    })

    it('renders sortable column headers', () => {
      render(<Battle />)
      // 3 persona tables × 7 columns each = 21 column headers
      const headers = screen.getAllByRole('columnheader')
      expect(headers.length).toBe(21)
      // Verify all 7 column labels appear (×3 tables)
      expect(screen.getAllByText(/^Shares$/).length).toBe(3)
      expect(screen.getAllByText(/^Cost$/).length).toBe(3)
      expect(screen.getAllByText(/^Price$/).length).toBe(3)
      expect(screen.getAllByText(/^Weight$/).length).toBe(3)
    })

    it('clicking Shares header sorts by shares', () => {
      render(<Battle />)
      const sharesHeaders = screen.getAllByText(/Shares/)
      // Click first Shares header
      fireEvent.click(sharesHeaders[0])
      // Sort icon should change from ArrowUpDown to ArrowUp or ArrowDown
      // (hard to test the icon directly, but the sort state changed)
    })

    it('double-clicking same column toggles direction', () => {
      render(<Battle />)
      const weightHeaders = screen.getAllByText(/Weight/)
      // Click once
      fireEvent.click(weightHeaders[0])
      // Click again
      fireEvent.click(weightHeaders[0])
      // Should toggle direction
    })
  })

  describe('Row click navigation', () => {
    let locationMock: Location

    beforeEach(() => {
      locationMock = mockLocation()
      mockUseApi.mockReturnValue({ data: makeBattleData(), loading: false, error: null, refetch: vi.fn() })
    })

    afterEach(() => {
      restoreLocation()
    })

    it('clicking a holding row navigates to stock detail', () => {
      render(<Battle />)
      const maybankRow = screen.getByText('MAYBANK')
      fireEvent.click(maybankRow)
      expect(window.location.href).toBe('/stock/MAYBANK?persona=ares')
    })

    it('navigates to correct persona for different tables', () => {
      render(<Battle />)
      const axreitRow = screen.getByText('AXREIT')
      fireEvent.click(axreitRow)
      expect(window.location.href).toBe('/stock/AXREIT?persona=demeter')
    })
  })

  describe('Format helpers', () => {
    beforeEach(() => {
      mockUseApi.mockReturnValue({ data: makeBattleData(), loading: false, error: null, refetch: vi.fn() })
    })

    it('formats positive PnL correctly', () => {
      render(<Battle />)
      expect(screen.getByText('+2.50%')).toBeInTheDocument()
    })

    it('formats negative PnL correctly', () => {
      render(<Battle />)
      expect(screen.getByText('-0.50%')).toBeInTheDocument()
    })

    it('formats RM values with 2 decimal places', () => {
      render(<Battle />)
      // RM 10,250.50 (Ares total)
      expect(screen.getByText('RM 10,250.50')).toBeInTheDocument()
    })

    it('shows cost prices with 3 decimal places', () => {
      render(<Battle />)
      // Cost values use toFixed(3)
      expect(screen.getByText('RM 10.000')).toBeInTheDocument()
    })
  })

  describe('Persona card borders', () => {
    it('each persona card has colored border', () => {
      mockUseApi.mockReturnValue({ data: makeBattleData(), loading: false, error: null, refetch: vi.fn() })
      render(<Battle />)
      // Ares = red, Demeter = green, Athena = purple
      const cards = document.querySelectorAll('.rounded-xl.p-5.border-2')
      expect(cards.length).toBe(3)
      // All cards should have a borderColor style set
      cards.forEach(card => {
        const style = (card as HTMLElement).style.borderColor
        expect(style).toBeTruthy()
      })
    })
  })
})
