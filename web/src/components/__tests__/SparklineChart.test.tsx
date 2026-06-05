import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import SparklineChart from '../SparklineChart'

describe('SparklineChart', () => {
  it('renders an SVG with data points', () => {
    const { container } = render(<SparklineChart data={[10, 20, 15, 25, 30]} />)
    const svg = container.querySelector('svg')
    expect(svg).toBeInTheDocument()
    // Should have a polyline for the sparkline
    const polyline = svg!.querySelector('polyline')
    expect(polyline).toBeInTheDocument()
    // Should have a polygon for the gradient fill
    const polygon = svg!.querySelector('polygon')
    expect(polygon).toBeInTheDocument()
  })

  it('returns null when data array is empty', () => {
    const { container } = render(<SparklineChart data={[]} />)
    expect(container.querySelector('svg')).not.toBeInTheDocument()
    expect(container.innerHTML).toBe('')
  })

  it('renders with a single data point', () => {
    const { container } = render(<SparklineChart data={[42]} />)
    const svg = container.querySelector('svg')
    expect(svg).toBeInTheDocument()
    // Should still render polyline and polygon for single point
    const polyline = svg!.querySelector('polyline')
    expect(polyline).toBeInTheDocument()
  })

  it('uses default dimensions when not specified', () => {
    const { container } = render(<SparklineChart data={[10, 20, 30]} />)
    const svg = container.querySelector('svg')
    expect(svg).toHaveAttribute('width', '80')
    expect(svg).toHaveAttribute('height', '30')
  })

  it('uses custom width and height', () => {
    const { container } = render(<SparklineChart data={[10, 20, 30]} width={120} height={50} />)
    const svg = container.querySelector('svg')
    expect(svg).toHaveAttribute('width', '120')
    expect(svg).toHaveAttribute('height', '50')
  })

  it('renders green color for uptrend (last >= first)', () => {
    const { container } = render(<SparklineChart data={[10, 15, 20]} />)
    const polyline = container.querySelector('polyline')
    expect(polyline).toHaveAttribute('stroke', '#059669') // green-600
  })

  it('renders red color for downtrend (last < first)', () => {
    const { container } = render(<SparklineChart data={[30, 20, 10]} />)
    const polyline = container.querySelector('polyline')
    expect(polyline).toHaveAttribute('stroke', '#ef4444') // red-500
  })

  it('uses custom color and ignores trend-based coloring', () => {
    const { container } = render(<SparklineChart data={[10, 20, 30]} color="#3b82f6" />)
    // When last >= first but custom color set, polyline stroke uses custom color
    // for uptrend; trend variable = "#3b82f6" since last >= first
    const polyline = container.querySelector('polyline')
    expect(polyline).toHaveAttribute('stroke', '#3b82f6')
  })

  it('renders correct viewBox attribute', () => {
    const { container } = render(<SparklineChart data={[10, 20]} width={100} height={40} />)
    const svg = container.querySelector('svg')
    expect(svg).toHaveAttribute('viewBox', '0 0 100 40')
  })

  it('generates correct number of polyline points matching data length', () => {
    const data = [10, 20, 15, 25, 30, 35, 28, 40]
    const { container } = render(<SparklineChart data={data} />)
    const polyline = container.querySelector('polyline')
    const points = polyline!.getAttribute('points')!
    // Each point is "x,y" separated by space
    const pointCount = points.split(' ').length
    expect(pointCount).toBe(data.length)
  })

  it('handles flat data (all same values)', () => {
    const { container } = render(<SparklineChart data={[25, 25, 25, 25]} />)
    const svg = container.querySelector('svg')
    expect(svg).toBeInTheDocument()
    // range = 0 → clamps to 1, should render without NaN
    const polyline = container.querySelector('polyline')
    const points = polyline!.getAttribute('points')!
    expect(points).not.toContain('NaN')
    // Flat data means last >= first → green
    expect(polyline).toHaveAttribute('stroke', '#059669')
  })

  it('renders with negative values', () => {
    const { container } = render(<SparklineChart data={[-5, -2, 0, 3, 1]} />)
    const svg = container.querySelector('svg')
    expect(svg).toBeInTheDocument()
    const polyline = svg!.querySelector('polyline')
    expect(polyline).toBeInTheDocument()
    // last (1) >= first (-5) → uptrend
    expect(polyline).toHaveAttribute('stroke', '#059669')
  })
})
