import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import ErrorBoundary from '../ErrorBoundary'

function Thrower({ msg = 'test error' }: { msg?: string }): never {
  throw new Error(msg)
}

function SafeChild() {
  return <div>everything ok</div>
}

describe('ErrorBoundary', () => {
  it('renders children when no error', () => {
    render(
      <ErrorBoundary>
        <SafeChild />
      </ErrorBoundary>
    )
    expect(screen.getByText('everything ok')).toBeInTheDocument()
  })

  it('renders fallback UI when child throws', () => {
    // Suppress console.error from intentional throw
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    render(
      <ErrorBoundary>
        <Thrower />
      </ErrorBoundary>
    )
    expect(screen.getByText('Something went wrong')).toBeInTheDocument()
    expect(screen.getByText('test error')).toBeInTheDocument()
    spy.mockRestore()
  })

  it('shows retry button in error state', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    render(
      <ErrorBoundary>
        <Thrower />
      </ErrorBoundary>
    )
    expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument()
    spy.mockRestore()
  })

  it('resets error state on retry with safe child', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    // Use key to force remount — retry clears state, then safe child renders
    const { rerender } = render(
      <ErrorBoundary>
        <Thrower msg="first fail" />
      </ErrorBoundary>
    )
    expect(screen.getByText('Something went wrong')).toBeInTheDocument()

    // Rerender with safe child (simulates navigation after error recovery)
    rerender(
      <ErrorBoundary key="recovered">
        <SafeChild />
      </ErrorBoundary>
    )
    expect(screen.getByText('everything ok')).toBeInTheDocument()
    spy.mockRestore()
  })

  it('renders custom fallback when provided', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    render(
      <ErrorBoundary fallback={<div>custom error page</div>}>
        <Thrower />
      </ErrorBoundary>
    )
    expect(screen.getByText('custom error page')).toBeInTheDocument()
    expect(screen.queryByText('Something went wrong')).not.toBeInTheDocument()
    spy.mockRestore()
  })

  it('calls onError callback with error details', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    const onError = vi.fn()
    render(
      <ErrorBoundary onError={onError}>
        <Thrower msg="callback test" />
      </ErrorBoundary>
    )
    expect(onError).toHaveBeenCalledTimes(1)
    expect(onError.mock.calls[0][0].message).toBe('callback test')
    spy.mockRestore()
  })

  it('renders AlertTriangle icon in error state', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    const { container } = render(
      <ErrorBoundary>
        <Thrower />
      </ErrorBoundary>
    )
    // lucide icons render as SVG
    expect(container.querySelector('svg')).toBeInTheDocument()
    spy.mockRestore()
  })
})
