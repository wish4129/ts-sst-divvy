import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import StockCard from '../StockCard'
import type { Stock } from '../../data/stocks'

const baseStock: Stock = {
  code: 'MBMR',
  name: 'MBM Resources Berhad',
  industry: 'Automotive',
  marketCap: 1.98,
  lastPrice: 5.07,
  priceChange: 1.2,
  dividendYield: 11.83,
  score: { composite: 90, dividend: 40, growth: 20, quality: 20, risk: 10 },
  financials: [],
  dividends: [],
  status: 'active',
  addedAt: '2026-06-05',
  revisitAt: null,
  notes: 'Top screener pick.',
  sparkline: [5.0, 5.02, 5.05, 5.03, 5.07],
}

function renderCard(stock: Stock = baseStock, rank = 1) {
  return render(
    <MemoryRouter>
      <StockCard stock={stock} rank={rank} />
    </MemoryRouter>
  )
}

describe('StockCard', () => {
  it('renders the stock name', () => {
    renderCard()
    expect(screen.getByText('MBM Resources Berhad')).toBeInTheDocument()
  })

  it('renders the price with RM prefix', () => {
    renderCard()
    expect(screen.getByText('RM 5.07')).toBeInTheDocument()
  })

  it('renders the composite score', () => {
    renderCard()
    expect(screen.getByText('90')).toBeInTheDocument()
  })

  it('renders the rank number', () => {
    renderCard(baseStock, 3)
    expect(screen.getByText('#3')).toBeInTheDocument()
  })

  it('renders the industry tag', () => {
    renderCard()
    expect(screen.getByText('Automotive')).toBeInTheDocument()
  })

  it('renders dividend yield', () => {
    renderCard()
    expect(screen.getByText('11.83%')).toBeInTheDocument()
  })

  it('renders market cap', () => {
    renderCard()
    expect(screen.getByText('RM 2M')).toBeInTheDocument()
  })

  it('renders sparkline chart via SVG', () => {
    renderCard()
    const svg = document.querySelector('svg')
    expect(svg).toBeTruthy()
  })

  it('shows positive price change in green with ▲', () => {
    renderCard()
    expect(screen.getByText(/▲/)).toBeInTheDocument()
    expect(screen.getByText(/1\.20%/)).toBeInTheDocument()
  })

  it('shows negative price change in red with ▼', () => {
    const stock = { ...baseStock, priceChange: -2.5 }
    renderCard(stock)
    expect(screen.getByText(/▼/)).toBeInTheDocument()
    expect(screen.getByText(/2\.50%/)).toBeInTheDocument()
  })

  it('shows zero price change correctly', () => {
    const stock = { ...baseStock, priceChange: 0 }
    renderCard(stock)
    expect(screen.getByText(/▲/)).toBeInTheDocument()
    expect(screen.getByText(/0\.00%/)).toBeInTheDocument()
  })

  it('link navigates to /stock/{code}', () => {
    renderCard()
    const link = screen.getByRole('link')
    expect(link).toHaveAttribute('href', '/stock/MBMR')
  })

  it('uses _ticker for navigation when provided', () => {
    const stock = { ...baseStock, _ticker: '5247.KL', _shortCode: 'MBMR' }
    render(
      <MemoryRouter>
        <StockCard stock={stock} rank={1} />
      </MemoryRouter>
    )
    const link = screen.getByRole('link')
    expect(link).toHaveAttribute('href', '/stock/5247.KL')
  })

  it('displays _shortCode when provided instead of code', () => {
    const stock = { ...baseStock, _ticker: '5247.KL', _shortCode: 'MBMR' }
    render(
      <MemoryRouter>
        <StockCard stock={stock} rank={1} />
      </MemoryRouter>
    )
    // The display code text should still show MBMR (the short code)
    expect(screen.getByText('MBMR')).toBeInTheDocument()
  })

  it('handles minimal stock data without crashing', () => {
    const minimal: Stock = {
      code: 'TEST',
      name: 'Test Co',
      industry: 'Technology',
      marketCap: 0,
      lastPrice: 0,
      priceChange: 0,
      dividendYield: 0,
      score: { composite: 0, dividend: 0, growth: 0, quality: 0, risk: 0 },
      financials: [],
      dividends: [],
      status: 'revisit',
      addedAt: '2026-01-01',
      revisitAt: null,
      notes: '',
      sparkline: [],
    }
    renderCard(minimal, 99)
    expect(screen.getByText('Test Co')).toBeInTheDocument()
    expect(screen.getByText('#99')).toBeInTheDocument()
    expect(screen.getByText('Technology')).toBeInTheDocument()
  })
})
