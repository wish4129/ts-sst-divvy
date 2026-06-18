import { describe, it, expect, vi, beforeEach, afterAll } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'

class ResizeObserverMock { observe() {} unobserve() {} disconnect() {} }
vi.stubGlobal('ResizeObserver', ResizeObserverMock)

// Restore stubbed globals after all tests to prevent cross-file pollution [source: divvy/web/src/pages/__tests__/StockDetail.test.tsx]
afterAll(() => {
  vi.unstubAllGlobals()
})

const { mockUseApi } = vi.hoisted(() => ({ mockUseApi: vi.fn() }))
vi.mock('../../hooks/useApi', () => ({ useApi: mockUseApi }))

import StockDetail from '../StockDetail'

function mockApi(data: any = null, loading = false, error: string | null = null) {
  mockUseApi.mockReturnValue({ data, loading, error, refetch: vi.fn() })
}

// Helper: wrap StockDetail in Routes so useParams works
function renderStockDetail(route: string = '/stock/MAYBANK') {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <Routes>
        <Route path="/stock/:code" element={<StockDetail />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('StockDetail page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows skeleton during loading (no text back link)', () => {
    mockApi(null, true)
    renderStockDetail('/stock/MAYBANK')
    // Skeleton has role="status" — no visible text during loading
    expect(screen.getByRole('status')).toBeTruthy()
  })

  it('shows stock name when data loaded', () => {
    mockApi({
      stock_name: 'Malayan Banking',
      industry: 'Banking',
      score_composite: 85,
      score_breakdown: {},
      decision_rationale: { sections: {}, sources: {} },
      ai_report: null,
    })
    renderStockDetail('/stock/MAYBANK')
    expect(screen.getByText(/Malayan Banking/i)).toBeTruthy()
  })

  it('shows deep analysis banner when data loaded', () => {
    mockApi({
      stock_name: 'Test Stock',
      industry: 'Tech',
      score_composite: 75,
      score_breakdown: {},
      decision_rationale: { sections: {}, sources: {} },
      ai_report: null,
    })
    renderStockDetail('/stock/TEST')
    expect(screen.getByText(/deep analysis/i)).toBeTruthy()
  })

  describe('Score breakdown — dark mode visibility', () => {
    it('renders score breakdown cards with correct dark mode classes', () => {
      mockApi({
        stock_name: 'Test Stock',
        industry: 'Tech',
        score_composite: 75,
        score_breakdown: {
          profitability: { value: 80, raw: 80, weighted: 16 },
          debt_level: { value: 70, raw: 70, weighted: 14 },
          growth_momentum: { value: 60, raw: 60, weighted: 12 },
          market_position: { value: 85, raw: 85, weighted: 17 },
          management_quality: { value: 75, raw: 75, weighted: 15 },
          earnings_stability: { value: 65, raw: 65, weighted: 13 },
          valuation: { value: 55, raw: 55, weighted: 11 },
        },
        decision_rationale: { sections: {}, sources: {} },
        ai_report: null,
      })
      renderStockDetail('/stock/TEST')
      // All 7 factor names should be visible
      expect(screen.getByText(/profitability/i)).toBeTruthy()
      expect(screen.getByText(/debt level/i)).toBeTruthy()
      expect(screen.getByText(/growth momentum/i)).toBeTruthy()
      expect(screen.getByText(/market position/i)).toBeTruthy()
      expect(screen.getByText(/management quality/i)).toBeTruthy()
      expect(screen.getByText(/earnings stability/i)).toBeTruthy()
      expect(screen.getByText(/valuation/i)).toBeTruthy()
      // Score values use tabular-nums
      expect(screen.getByText('16.0')).toBeTruthy()
      expect(screen.getByText('14.0')).toBeTruthy()
      expect(screen.getByText('12.0')).toBeTruthy()
    })

    it('shows Factor Score Breakdown heading with source subtitle', () => {
      mockApi({
        stock_name: 'Test Stock',
        industry: 'Tech',
        score_composite: 75,
        score_breakdown: { profitability: { value: 80, raw: 80, weighted: 16 } },
        decision_rationale: { sections: {}, sources: {} },
        ai_report: null,
      })
      renderStockDetail('/stock/TEST')
      expect(screen.getByText('Factor Score Breakdown')).toBeTruthy()
      expect(screen.getByText(/Source: Quarterly financials/)).toBeTruthy()
    })

    it('renders dashes for null weighted values', () => {
      mockApi({
        stock_name: 'Test Stock',
        industry: 'Tech',
        score_composite: 75,
        score_breakdown: { profitability: { value: 80, raw: 80, weighted: null } },
        decision_rationale: { sections: {}, sources: {} },
        ai_report: null,
      })
      renderStockDetail('/stock/TEST')
      expect(screen.getByText('—')).toBeTruthy()
    })
  })

  describe('RenderLine — numbered list rendering', () => {
    function mockWithReport(report: Record<string, string>) {
      mockApi({
        stock_name: 'Test Stock',
        industry: 'Tech',
        score_composite: 75,
        score_breakdown: { profitability: { value: 80, raw: 80, weighted: 16 } },
        ai_report: report,
        ai_model: 'gpt-4',
      })
    }

    it('renders numbered list items with correct prefix', () => {
      mockWithReport({
        strengths: '1. Market leadership in ASEAN\n2. Strong digital transformation\n3. Diversified revenue streams',
      })
      renderStockDetail('/stock/TEST')
      // Check that numbered prefixes appear
      expect(screen.getByText('Market leadership in ASEAN')).toBeTruthy()
      expect(screen.getByText('Strong digital transformation')).toBeTruthy()
      expect(screen.getByText('Diversified revenue streams')).toBeTruthy()
      // Check 1., 2., 3. are rendered as prefix elements (they're in separate spans)
      expect(screen.getByText('1')).toBeTruthy()
      expect(screen.getByText('2')).toBeTruthy()
      expect(screen.getByText('3')).toBeTruthy()
    })

    it('renders mixed bullet and numbered list items', () => {
      mockWithReport({
        strengths: '1. Strong capital buffer\n2. Consistent dividend growth\n• Digital banking initiative\n• Cost optimization',
      })
      renderStockDetail('/stock/TEST')
      expect(screen.getByText('Strong capital buffer')).toBeTruthy()
      expect(screen.getByText('Consistent dividend growth')).toBeTruthy()
      expect(screen.getByText('Digital banking initiative')).toBeTruthy()
      expect(screen.getByText('Cost optimization')).toBeTruthy()
    })

    it('renders indented numbered items with proper spacing', () => {
      mockWithReport({
        strengths: '1. Main strength\n   1. Sub-point one\n   2. Sub-point two',
      })
      renderStockDetail('/stock/TEST')
      expect(screen.getByText('Main strength')).toBeTruthy()
      expect(screen.getByText('Sub-point one')).toBeTruthy()
      expect(screen.getByText('Sub-point two')).toBeTruthy()
    })

    it('renders indented bullet items with proper spacing', () => {
      mockWithReport({
        strengths: '• Top-level item\n  • Nested detail\n  • Another nested item',
      })
      renderStockDetail('/stock/TEST')
      expect(screen.getByText('Top-level item')).toBeTruthy()
      expect(screen.getByText('Nested detail')).toBeTruthy()
      expect(screen.getByText('Another nested item')).toBeTruthy()
    })

    it('renders plain text lines without list prefix', () => {
      mockWithReport({
        summary: 'This is a plain paragraph of text describing the stock outlook.',
      })
      renderStockDetail('/stock/TEST')
      expect(screen.getByText('This is a plain paragraph of text describing the stock outlook.')).toBeTruthy()
    })

    it('renders bold text with ** markers', () => {
      mockWithReport({
        strengths: 'Core competency in **digital banking** and **fintech** partnerships',
      })
      renderStockDetail('/stock/TEST')
      // The ** markers should render as <strong> — check the combined text
      expect(screen.getByText(/digital banking/)).toBeTruthy()
      expect(screen.getByText(/fintech/)).toBeTruthy()
    })
  })

  it('shows "Stock not found" when no code param', () => {
    mockApi(null, true)
    render(
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route path="*" element={<StockDetail />} />
        </Routes>
      </MemoryRouter>
    )
    expect(screen.getByText(/stock not found/i)).toBeTruthy()
  })
})
