import { describe, it, expect, vi } from 'vitest'
import { render } from '@testing-library/react'
import ProgressBar from '../ProgressBar'

describe('ProgressBar', () => {
  it('renders with hidden aria role', () => {
    const { container } = render(<ProgressBar />)
    const bar = container.querySelector('[aria-hidden="true"]')
    expect(bar).toBeTruthy()
  })

  it('renders fixed position container', () => {
    const { container } = render(<ProgressBar />)
    const container_ = container.firstElementChild
    expect(container_?.className).toContain('fixed')
    expect(container_?.className).toContain('top-0')
  })

  it('has inner bar div with gradient class', () => {
    const { container } = render(<ProgressBar />)
    const bar = container.querySelector('.bg-gradient-to-r')
    expect(bar).toBeTruthy()
  })

  it('starts with width 0%', () => {
    const { container } = render(<ProgressBar />)
    const bar = container.querySelector('.bg-gradient-to-r') as HTMLElement
    expect(bar?.style.width).toBe('0%')
  })
})
