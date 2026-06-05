import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import ScoreBadge from '../ScoreBadge'

describe('ScoreBadge', () => {
  it('renders the score number', () => {
    render(<ScoreBadge score={42} />)
    expect(screen.getByText('42')).toBeInTheDocument()
  })

  it('renders red color for scores 0-49', () => {
    render(<ScoreBadge score={30} />)
    const span = screen.getByText('30')
    expect(span.className).toContain('text-red-700')
  })

  it('renders amber color for scores 50-69', () => {
    render(<ScoreBadge score={60} />)
    const span = screen.getByText('60')
    expect(span.className).toContain('text-amber-700')
  })

  it('renders green color for scores 70-100', () => {
    render(<ScoreBadge score={85} />)
    const span = screen.getByText('85')
    expect(span.className).toContain('text-emerald-700')
  })

  it('renders small size variant with correct width', () => {
    render(<ScoreBadge score={50} size="sm" />)
    const svg = document.querySelector('svg')
    expect(svg).toHaveAttribute('width', '40')
  })

  it('renders medium size variant (default) with correct width', () => {
    render(<ScoreBadge score={50} />)
    const svg = document.querySelector('svg')
    expect(svg).toHaveAttribute('width', '56')
  })

  it('renders large size variant with correct width', () => {
    render(<ScoreBadge score={50} size="lg" />)
    const svg = document.querySelector('svg')
    expect(svg).toHaveAttribute('width', '72')
  })

  it('handles edge case: score=0 (minimum)', () => {
    render(<ScoreBadge score={0} />)
    expect(screen.getByText('0')).toBeInTheDocument()
  })

  it('handles edge case: score=100 (maximum)', () => {
    render(<ScoreBadge score={100} />)
    expect(screen.getByText('100')).toBeInTheDocument()
  })
})
