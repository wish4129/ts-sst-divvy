import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'

class ResizeObserverMock { observe() {} unobserve() {} disconnect() {} }
window.ResizeObserver = ResizeObserverMock as any

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
      personas: { ares: {}, demeter: {}, athena: {} },
      score_breakdown: {},
      decision_rationale: { sections: {}, sources: {} },
      ai_report: null,
    })
    renderStockDetail('/stock/MAYBANK')
    expect(screen.getByText(/Malayan Banking/i)).toBeTruthy()
  })

  it('shows persona analysis banner when data loaded', () => {
    mockApi({
      stock_name: 'Test Stock',
      persona: 'ares',
      industry: 'Tech',
      score_composite: 75,
      personas: {
        ares: { decision: 'HOLD' },
        demeter: { decision: 'BUY' },
        athena: { decision: 'SELL' },
      },
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
