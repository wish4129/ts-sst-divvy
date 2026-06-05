import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, act } from '@testing-library/react'
import { renderHook } from '@testing-library/react'
import type { ReactNode } from 'react'

// All mocks must be inside vi.hoisted() since it runs before module code
const {
  mockSignInWithOAuth,
  mockSignOut,
  mockGetSession,
  mockOnAuthStateChange,
  mockSubscribe,
  mockSupabase,
} = vi.hoisted(() => {
  let onAuthStateChangeCallback: ((event: string, session: any) => void) | null = null
  const subscribe = vi.fn()

  return {
    mockSignInWithOAuth: vi.fn(),
    mockSignOut: vi.fn(),
    mockGetSession: vi.fn(),
    mockOnAuthStateChange: vi.fn().mockImplementation((callback: any) => {
      onAuthStateChangeCallback = callback
      // Store callback so tests can access it
      ;(mockOnAuthStateChange as any)._callback = callback
      return { data: { subscription: { unsubscribe: subscribe } } }
    }),
    mockSubscribe: subscribe,
    mockSupabase: {
      auth: {
        signInWithOAuth: undefined as any,  // filled below
        signOut: undefined as any,
        getSession: undefined as any,
        onAuthStateChange: undefined as any,
      },
    },
  }
})

// Wire up mocks after hoisting
mockSupabase.auth.signInWithOAuth = mockSignInWithOAuth
mockSupabase.auth.signOut = mockSignOut
mockSupabase.auth.getSession = mockGetSession
mockSupabase.auth.onAuthStateChange = mockOnAuthStateChange

vi.mock('../supabase', () => ({
  supabase: mockSupabase,
}))

import { AuthProvider, useAuth } from '../AuthContext'

// Helper to get the current auth state change callback
function getCallback() {
  return (mockOnAuthStateChange as any)._callback as ((event: string, session: any) => void) | null
}

// Mock window.location
const originalLocation = window.location

function TestConsumer() {
  const auth = useAuth()
  return (
    <div>
      <span data-testid="loading">{String(auth.loading)}</span>
      <span data-testid="user">{auth.user ? auth.user.id : 'null'}</span>
      <span data-testid="email">{auth.user?.email || 'null'}</span>
      <button data-testid="signin" onClick={() => auth.signInWithGoogle()}>Sign In</button>
      <button data-testid="signout" onClick={() => auth.signOut()}>Sign Out</button>
    </div>
  )
}

function renderWithProvider(ui: ReactNode) {
  return render(<AuthProvider>{ui}</AuthProvider>)
}

describe('AuthContext', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Reset callback
    ;(mockOnAuthStateChange as any)._callback = null
    // Default: no session
    mockGetSession.mockResolvedValue({ data: { session: null } })
  })

  afterEach(() => {
    Object.defineProperty(window, 'location', {
      value: originalLocation,
      writable: true,
    })
  })

  describe('useAuth guard', () => {
    it('throws when used outside AuthProvider', () => {
      const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
      expect(() => render(<TestConsumer />)).toThrow('useAuth must be used within AuthProvider')
      spy.mockRestore()
    })
  })

  describe('AuthProvider initial state', () => {
    it('starts with loading=true', async () => {
      let resolveSession: (value: any) => void
      mockGetSession.mockReturnValue(new Promise(resolve => { resolveSession = resolve }))

      renderWithProvider(<TestConsumer />)

      expect(screen.getByTestId('loading').textContent).toBe('true')
      expect(screen.getByTestId('user').textContent).toBe('null')
    })

    it('calls getSession on mount to check existing session', async () => {
      renderWithProvider(<TestConsumer />)
      await waitFor(() => expect(screen.getByTestId('loading').textContent).toBe('false'))
      expect(mockGetSession).toHaveBeenCalledTimes(1)
    })

    it('subscribes to onAuthStateChange on mount', async () => {
      renderWithProvider(<TestConsumer />)
      await waitFor(() => expect(screen.getByTestId('loading').textContent).toBe('false'))
      expect(mockOnAuthStateChange).toHaveBeenCalledTimes(1)
    })

    it('sets loading=false after getSession resolves', async () => {
      mockGetSession.mockResolvedValue({ data: { session: null } })

      renderWithProvider(<TestConsumer />)

      await waitFor(() => {
        expect(screen.getByTestId('loading').textContent).toBe('false')
      })
    })
  })

  describe('Session loading', () => {
    it('sets user when session is returned from getSession', async () => {
      const mockUser = { id: 'user-123', email: 'kevin@example.com', user_metadata: {} }
      mockGetSession.mockResolvedValue({
        data: { session: { user: mockUser, access_token: 'tok', refresh_token: 'ref' } },
      })

      renderWithProvider(<TestConsumer />)

      await waitFor(() => {
        expect(screen.getByTestId('user').textContent).toBe('user-123')
        expect(screen.getByTestId('email').textContent).toBe('kevin@example.com')
      })
    })

    it('sets user to null when no session', async () => {
      mockGetSession.mockResolvedValue({ data: { session: null } })

      renderWithProvider(<TestConsumer />)

      await waitFor(() => {
        expect(screen.getByTestId('user').textContent).toBe('null')
        expect(screen.getByTestId('loading').textContent).toBe('false')
      })
    })
  })

  describe('Auth state change listener', () => {
    it('updates user on SIGNED_IN event', async () => {
      mockGetSession.mockResolvedValue({ data: { session: null } })

      renderWithProvider(<TestConsumer />)
      await waitFor(() => expect(screen.getByTestId('loading').textContent).toBe('false'))

      const mockUser = { id: 'new-user', email: 'new@example.com', user_metadata: {} }
      const cb = getCallback()
      await act(async () => {
        cb?.('SIGNED_IN', { user: mockUser })
      })

      expect(screen.getByTestId('user').textContent).toBe('new-user')
      expect(screen.getByTestId('email').textContent).toBe('new@example.com')
    })

    it('clears user on SIGNED_OUT event', async () => {
      const mockUser = { id: 'user-456', email: 'out@example.com', user_metadata: {} }
      mockGetSession.mockResolvedValue({
        data: { session: { user: mockUser, access_token: 'tok', refresh_token: 'ref' } },
      })

      renderWithProvider(<TestConsumer />)
      await waitFor(() => expect(screen.getByTestId('user').textContent).toBe('user-456'))

      const cb = getCallback()
      await act(async () => {
        cb?.('SIGNED_OUT', null)
      })

      expect(screen.getByTestId('user').textContent).toBe('null')
    })

    it('sets loading=false after auth state change', async () => {
      mockGetSession.mockResolvedValue({ data: { session: null } })

      renderWithProvider(<TestConsumer />)
      await waitFor(() => expect(screen.getByTestId('loading').textContent).toBe('false'))

      const mockUser = { id: 'user-789', email: 'state@example.com', user_metadata: {} }
      const cb = getCallback()
      await act(async () => {
        cb?.('SIGNED_IN', { user: mockUser })
      })

      expect(screen.getByTestId('loading').textContent).toBe('false')
    })
  })

  describe('signInWithGoogle', () => {
    it('calls supabase.auth.signInWithOAuth with google provider', async () => {
      mockGetSession.mockResolvedValue({ data: { session: null } })
      mockSignInWithOAuth.mockResolvedValue({})

      renderWithProvider(<TestConsumer />)
      await waitFor(() => expect(screen.getByTestId('loading').textContent).toBe('false'))

      await act(async () => {
        screen.getByTestId('signin').click()
      })

      expect(mockSignInWithOAuth).toHaveBeenCalledTimes(1)
      expect(mockSignInWithOAuth).toHaveBeenCalledWith({
        provider: 'google',
        options: { redirectTo: expect.stringContaining('/auth/callback') },
      })
    })

    it('includes window.location.origin in redirect URL', async () => {
      mockGetSession.mockResolvedValue({ data: { session: null } })
      mockSignInWithOAuth.mockResolvedValue({})

      Object.defineProperty(window, 'location', {
        value: { origin: 'https://divvy.example.com' },
        writable: true,
      })

      renderWithProvider(<TestConsumer />)
      await waitFor(() => expect(screen.getByTestId('loading').textContent).toBe('false'))

      await act(async () => {
        screen.getByTestId('signin').click()
      })

      expect(mockSignInWithOAuth).toHaveBeenCalledWith({
        provider: 'google',
        options: { redirectTo: 'https://divvy.example.com/auth/callback' },
      })
    })
  })

  describe('signOut', () => {
    it('calls supabase.auth.signOut', async () => {
      const mockUser = { id: 'user-999', email: 'out@example.com', user_metadata: {} }
      mockGetSession.mockResolvedValue({
        data: { session: { user: mockUser, access_token: 'tok', refresh_token: 'ref' } },
      })
      mockSignOut.mockResolvedValue({})

      renderWithProvider(<TestConsumer />)
      await waitFor(() => expect(screen.getByTestId('user').textContent).toBe('user-999'))

      await act(async () => {
        screen.getByTestId('signout').click()
      })

      expect(mockSignOut).toHaveBeenCalledTimes(1)
    })
  })

  describe('Cleanup', () => {
    it('unsubscribes on unmount', () => {
      mockGetSession.mockResolvedValue({ data: { session: null } })

      const { unmount } = renderWithProvider(<TestConsumer />)

      unmount()

      expect(mockSubscribe).toHaveBeenCalledTimes(1)
    })
  })

  describe('Token refresh / TOKEN_REFRESHED event', () => {
    it('updates session on TOKEN_REFRESHED', async () => {
      const oldUser = { id: 'old-user', email: 'old@example.com', user_metadata: {} }
      mockGetSession.mockResolvedValue({
        data: { session: { user: oldUser, access_token: 'tok', refresh_token: 'ref' } },
      })

      renderWithProvider(<TestConsumer />)
      await waitFor(() => expect(screen.getByTestId('user').textContent).toBe('old-user'))

      const refreshedUser = { id: 'refreshed-user', email: 'refreshed@example.com', user_metadata: {} }
      const cb = getCallback()
      await act(async () => {
        cb?.('TOKEN_REFRESHED', { user: refreshedUser })
      })

      expect(screen.getByTestId('user').textContent).toBe('refreshed-user')
    })
  })

  describe('Multiple consumers', () => {
    it('provides same auth state to all consumers', async () => {
      const mockUser = { id: 'shared-user', email: 'shared@example.com', user_metadata: {} }
      mockGetSession.mockResolvedValue({
        data: { session: { user: mockUser, access_token: 'tok', refresh_token: 'ref' } },
      })

      renderWithProvider(
        <>
          <TestConsumer />
          <TestConsumer />
        </>
      )

      await waitFor(() => {
        const users = screen.getAllByTestId('user')
        expect(users).toHaveLength(2)
        expect(users[0].textContent).toBe('shared-user')
        expect(users[1].textContent).toBe('shared-user')
      })
    })
  })

  describe('useAuth hook', () => {
    it('returns signInWithGoogle and signOut functions', async () => {
      mockGetSession.mockResolvedValue({ data: { session: null } })

      const { result } = renderHook(() => useAuth(), {
        wrapper: ({ children }: { children: ReactNode }) => (
          <AuthProvider>{children}</AuthProvider>
        ),
      })

      await waitFor(() => expect(result.current.loading).toBe(false))

      expect(typeof result.current.signInWithGoogle).toBe('function')
      expect(typeof result.current.signOut).toBe('function')
    })

    it('returns null user initially while loading', () => {
      let resolveSession: (value: any) => void
      mockGetSession.mockReturnValue(new Promise(resolve => { resolveSession = resolve }))

      const { result } = renderHook(() => useAuth(), {
        wrapper: ({ children }: { children: ReactNode }) => (
          <AuthProvider>{children}</AuthProvider>
        ),
      })

      expect(result.current.user).toBeNull()
      expect(result.current.loading).toBe(true)
    })
  })
})
