import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'

const { mockUseAuth } = vi.hoisted(() => ({
  mockUseAuth: vi.fn(),
}))

vi.mock('../../lib/AuthContext', () => ({
  useAuth: mockUseAuth,
}))

import LoginGate from '../LoginGate'

describe('LoginGate', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows Loading when auth is loading', () => {
    mockUseAuth.mockReturnValue({ user: null, loading: true })

    render(
      <LoginGate>
        <p>child content</p>
      </LoginGate>
    )

    expect(screen.getByRole('status')).toBeInTheDocument()
    expect(screen.queryByText('child content')).not.toBeInTheDocument()
  })

  it('shows sign-in message when user is null and not loading', () => {
    mockUseAuth.mockReturnValue({ user: null, loading: false })

    render(
      <LoginGate>
        <p>child content</p>
      </LoginGate>
    )

    expect(screen.getByText('Sign in to manage your portfolio')).toBeInTheDocument()
    expect(screen.queryByText('child content')).not.toBeInTheDocument()
  })

  it('renders children when user is authenticated', () => {
    mockUseAuth.mockReturnValue({ user: { id: '123' }, loading: false })

    render(
      <LoginGate>
        <p>child content</p>
      </LoginGate>
    )

    expect(screen.getByText('child content')).toBeInTheDocument()
    expect(screen.queryByText('Sign in to manage your portfolio')).not.toBeInTheDocument()
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })
})
