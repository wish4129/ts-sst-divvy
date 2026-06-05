import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import Loading from '../Loading'

describe('Loading', () => {
  it('renders the spinner', () => {
    render(<Loading />)
    const spinner = screen.getByRole('status')
    expect(spinner).toBeInTheDocument()
  })

  it('has accessible label', () => {
    render(<Loading />)
    const spinner = screen.getByRole('status')
    expect(spinner).toHaveAttribute('aria-label', 'Loading')
  })

  it('renders the spinner with animation classes', () => {
    render(<Loading />)
    const spinner = screen.getByRole('status')
    expect(spinner.className).toContain('animate-spin')
    expect(spinner.className).toContain('rounded-full')
    expect(spinner.className).toContain('border-b-2')
    expect(spinner.className).toContain('border-emerald-600')
  })

  it('renders in a full-screen centered container', () => {
    const { container } = render(<Loading />)
    const wrapper = container.firstChild as HTMLElement
    expect(wrapper.className).toContain('flex')
    expect(wrapper.className).toContain('items-center')
    expect(wrapper.className).toContain('justify-center')
    expect(wrapper.className).toContain('min-h-screen')
  })

  it('renders a visually hidden text for screen readers', () => {
    render(<Loading />)
    expect(screen.getByText('Loading...')).toBeInTheDocument()
  })
})
