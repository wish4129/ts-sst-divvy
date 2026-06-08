import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import AuthCallback from '../AuthCallback'

const { mockUseAuth } = vi.hoisted(() => ({ mockUseAuth: vi.fn() }))
vi.mock('../../lib/AuthContext', () => ({ useAuth: mockUseAuth }))

describe('AuthCallback page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows spinner while loading', () => {
    mockUseAuth.mockReturnValue({ user: null, loading: true })
    render(
      <MemoryRouter initialEntries={['/auth/callback']}>
        <AuthCallback />
      </MemoryRouter>
    )
    const spinner = document.querySelector('.animate-spin')
    expect(spinner).toBeTruthy()
  })

  it('renders without crashing when loaded', () => {
    mockUseAuth.mockReturnValue({ user: null, loading: false })
    render(
      <MemoryRouter initialEntries={['/auth/callback']}>
        <AuthCallback />
      </MemoryRouter>
    )
    // Component should still render (navigate called in useEffect)
    expect(document.body).toBeTruthy()
  })

  it('renders centered layout', () => {
    mockUseAuth.mockReturnValue({ user: null, loading: true })
    render(
      <MemoryRouter initialEntries={['/auth/callback']}>
        <AuthCallback />
      </MemoryRouter>
    )
    const container = document.querySelector('.min-h-screen')
    expect(container?.className).toContain('flex')
    expect(container?.className).toContain('justify-center')
  })
})
