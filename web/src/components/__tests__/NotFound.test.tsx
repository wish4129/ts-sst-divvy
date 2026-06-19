import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import NotFound from '../NotFound'

describe('NotFound', () => {
  it('renders the 404 heading', () => {
    render(
      <MemoryRouter>
        <NotFound />
      </MemoryRouter>
    )
    expect(screen.getByText('404')).toBeInTheDocument()
  })

  it('renders the page not found message', () => {
    render(
      <MemoryRouter>
        <NotFound />
      </MemoryRouter>
    )
    expect(screen.getByText('Page not found')).toBeInTheDocument()
  })

  it('renders a back-link to the dashboard', () => {
    render(
      <MemoryRouter>
        <NotFound />
      </MemoryRouter>
    )
    const link = screen.getByRole('link', { name: /back to dashboard/i })
    expect(link).toBeInTheDocument()
    expect(link).toHaveAttribute('href', '/')
  })

  it('back-link has emerald button styling', () => {
    render(
      <MemoryRouter>
        <NotFound />
      </MemoryRouter>
    )
    const link = screen.getByRole('link', { name: /back to dashboard/i })
    expect(link.className).toContain('bg-emerald-600')
  })

  it('links have mobile touch targets (min-h-[44px])', () => {
    render(
      <MemoryRouter>
        <NotFound />
      </MemoryRouter>
    )
    const links = screen.getAllByRole('link')
    links.forEach(link => {
      expect(link.className).toContain('min-h-[44px]')
    })
  })

  it('has a secondary link to browse stocks', () => {
    render(
      <MemoryRouter>
        <NotFound />
      </MemoryRouter>
    )
    expect(screen.getByRole('link', { name: /browse stocks/i })).toBeInTheDocument()
  })
})
