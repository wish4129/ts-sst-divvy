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
