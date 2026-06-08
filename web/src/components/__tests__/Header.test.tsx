import { describe, it, expect, vi, beforeEach, afterAll } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

const { mockUseAuth } = vi.hoisted(() => ({
  mockUseAuth: vi.fn(),
}))

vi.mock('../../lib/AuthContext', () => ({
  useAuth: mockUseAuth,
}))

// Mock localStorage for theme tests
const localStorageMock = (() => {
  let store: Record<string, string> = {}
  return {
    getItem: vi.fn((key: string) => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => { store[key] = value }),
    removeItem: vi.fn((key: string) => { delete store[key] }),
    clear: vi.fn(() => { store = {} }),
  }
})()

// Use vi.stubGlobal for proper sandboxing (vitest auto-cleans)
// localStorage needs Object.defineProperty pair for jsdom accessor properties
const _origLocalStorage = window.localStorage
Object.defineProperty(window, 'localStorage', { value: localStorageMock })
vi.stubGlobal('localStorage', localStorageMock)

const matchMediaMock = vi.fn().mockImplementation((query: string) => ({
  matches: false,
  media: query,
  onchange: null,
  addListener: vi.fn(),
  removeListener: vi.fn(),
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
  dispatchEvent: vi.fn(),
}))
vi.stubGlobal('matchMedia', matchMediaMock)

// Restore stubbed globals after all tests to prevent cross-file pollution [source: divvy/web/src/components/__tests__/Header.test.tsx]
afterAll(() => {
  vi.unstubAllGlobals()
  // Also restore window.localStorage if it was redefined
  try { Object.defineProperty(window, 'localStorage', { value: _origLocalStorage, writable: true, configurable: true }) } catch {}
})

import Header from '../Header'

function renderHeader(initialRoute = '/') {
  return render(
    <MemoryRouter initialEntries={[initialRoute]}>
      <Header />
    </MemoryRouter>
  )
}

describe('Header', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorageMock.clear()
  })

  describe('Branding', () => {
    it('renders the Divvy brand name', () => {
      mockUseAuth.mockReturnValue({ user: null, loading: false, signInWithGoogle: vi.fn(), signOut: vi.fn() })
      renderHeader()
      expect(screen.getByText('Divvy')).toBeInTheDocument()
    })

    it('brand links to home page', () => {
      mockUseAuth.mockReturnValue({ user: null, loading: false, signInWithGoogle: vi.fn(), signOut: vi.fn() })
      renderHeader()
      const brandLink = screen.getByText('Divvy').closest('a')
      expect(brandLink).toHaveAttribute('href', '/')
    })
  })

  describe('Navigation links', () => {
    it('renders Dashboard link', () => {
      mockUseAuth.mockReturnValue({ user: null, loading: false, signInWithGoogle: vi.fn(), signOut: vi.fn() })
      renderHeader()
      const links = screen.getAllByRole('link')
      const dashboardLink = links.find(l => l.getAttribute('href') === '/')
      expect(dashboardLink).toBeTruthy()
    })

    it('renders Watchlist link', () => {
      mockUseAuth.mockReturnValue({ user: null, loading: false, signInWithGoogle: vi.fn(), signOut: vi.fn() })
      renderHeader()
      const watchlistLink = screen.getByRole('link', { name: /watchlist/i })
      expect(watchlistLink).toHaveAttribute('href', '/watchlist')
    })

    it('renders Universe link', () => {
      mockUseAuth.mockReturnValue({ user: null, loading: false, signInWithGoogle: vi.fn(), signOut: vi.fn() })
      renderHeader()
      const universeLink = screen.getByRole('link', { name: /universe/i })
      expect(universeLink).toHaveAttribute('href', '/universe')
    })

    it('renders Battle link', () => {
      mockUseAuth.mockReturnValue({ user: null, loading: false, signInWithGoogle: vi.fn(), signOut: vi.fn() })
      renderHeader()
      const battleLink = screen.getByRole('link', { name: /battle/i })
      expect(battleLink).toHaveAttribute('href', '/battle')
    })

    it('highlights active nav link based on current route', () => {
      mockUseAuth.mockReturnValue({ user: null, loading: false, signInWithGoogle: vi.fn(), signOut: vi.fn() })
      renderHeader('/watchlist')
      const watchlistLink = screen.getByRole('link', { name: /watchlist/i })
      expect(watchlistLink.className).toContain('bg-emerald-100')
    })

    it('does not highlight inactive nav links', () => {
      mockUseAuth.mockReturnValue({ user: null, loading: false, signInWithGoogle: vi.fn(), signOut: vi.fn() })
      renderHeader('/battle')
      const watchlistLink = screen.getByRole('link', { name: /watchlist/i })
      expect(watchlistLink.className).not.toContain('bg-emerald-100')
    })
  })

  describe('Unauthenticated state', () => {
    it('renders sign-in button when user is null', () => {
      mockUseAuth.mockReturnValue({ user: null, loading: false, signInWithGoogle: vi.fn(), signOut: vi.fn() })
      renderHeader()
      expect(screen.getByText('Sign in')).toBeInTheDocument()
    })

    it('does not render avatar or user name when logged out', () => {
      mockUseAuth.mockReturnValue({ user: null, loading: false, signInWithGoogle: vi.fn(), signOut: vi.fn() })
      renderHeader()
      expect(screen.queryByRole('img')).not.toBeInTheDocument()
      expect(screen.queryByTitle('Sign out')).not.toBeInTheDocument()
    })

    it('calls signInWithGoogle when sign-in button clicked', () => {
      const signIn = vi.fn()
      mockUseAuth.mockReturnValue({ user: null, loading: false, signInWithGoogle: signIn, signOut: vi.fn() })
      renderHeader()
      fireEvent.click(screen.getByText('Sign in'))
      expect(signIn).toHaveBeenCalledTimes(1)
    })
  })

  describe('Loading state', () => {
    it('renders skeleton avatar when auth is loading', () => {
      mockUseAuth.mockReturnValue({ user: null, loading: true, signInWithGoogle: vi.fn(), signOut: vi.fn() })
      renderHeader()
      // The pulse animation div acts as a loading skeleton
      const skeleton = document.querySelector('.animate-pulse')
      expect(skeleton).toBeTruthy()
    })

    it('does not render sign-in button while loading', () => {
      mockUseAuth.mockReturnValue({ user: null, loading: true, signInWithGoogle: vi.fn(), signOut: vi.fn() })
      renderHeader()
      expect(screen.queryByText('Sign in')).not.toBeInTheDocument()
    })
  })

  describe('Authenticated state', () => {
    it('renders user name when authenticated', () => {
      mockUseAuth.mockReturnValue({
        user: { id: '123', email: 'test@example.com', user_metadata: { full_name: 'Kevin Mun' } },
        loading: false,
        signInWithGoogle: vi.fn(),
        signOut: vi.fn(),
      })
      renderHeader()
      expect(screen.getByText('Kevin Mun')).toBeInTheDocument()
    })

    it('falls back to email when full_name is not available', () => {
      mockUseAuth.mockReturnValue({
        user: { id: '123', email: 'test@example.com', user_metadata: {} },
        loading: false,
        signInWithGoogle: vi.fn(),
        signOut: vi.fn(),
      })
      renderHeader()
      expect(screen.getByText('test@example.com')).toBeInTheDocument()
    })

    it('renders avatar image when avatar_url is available', () => {
      mockUseAuth.mockReturnValue({
        user: {
          id: '123',
          email: 'test@example.com',
          user_metadata: { full_name: 'Kevin', avatar_url: 'https://example.com/avatar.jpg' },
        },
        loading: false,
        signInWithGoogle: vi.fn(),
        signOut: vi.fn(),
      })
      renderHeader()
      // alt="" gives role="presentation", not "img"
      const img = document.querySelector('img[src="https://example.com/avatar.jpg"]')
      expect(img).toBeTruthy()
      expect(img).toHaveAttribute('src', 'https://example.com/avatar.jpg')
    })

    it('renders default User icon when no avatar_url', () => {
      mockUseAuth.mockReturnValue({
        user: { id: '123', email: 'test@example.com', user_metadata: { full_name: 'Kevin' } },
        loading: false,
        signInWithGoogle: vi.fn(),
        signOut: vi.fn(),
      })
      renderHeader()
      // User icon is rendered as an SVG within a div
      const userIconContainer = document.querySelector('.w-7.h-7.rounded-full')
      expect(userIconContainer).toBeTruthy()
    })

    it('renders sign-out button when authenticated', () => {
      mockUseAuth.mockReturnValue({
        user: { id: '123', email: 'test@example.com', user_metadata: {} },
        loading: false,
        signInWithGoogle: vi.fn(),
        signOut: vi.fn(),
      })
      renderHeader()
      expect(screen.getByTitle('Sign out')).toBeInTheDocument()
    })

    it('calls signOut when sign-out button clicked', () => {
      const signOut = vi.fn()
      mockUseAuth.mockReturnValue({
        user: { id: '123', email: 'test@example.com', user_metadata: {} },
        loading: false,
        signInWithGoogle: vi.fn(),
        signOut,
      })
      renderHeader()
      fireEvent.click(screen.getByTitle('Sign out'))
      expect(signOut).toHaveBeenCalledTimes(1)
    })

    it('does not render sign-in button when authenticated', () => {
      mockUseAuth.mockReturnValue({
        user: { id: '123', email: 'test@example.com', user_metadata: {} },
        loading: false,
        signInWithGoogle: vi.fn(),
        signOut: vi.fn(),
      })
      renderHeader()
      expect(screen.queryByText('Sign in')).not.toBeInTheDocument()
    })
  })

  describe('Dark mode toggle', () => {
    it('renders dark mode toggle button', () => {
      mockUseAuth.mockReturnValue({ user: null, loading: false, signInWithGoogle: vi.fn(), signOut: vi.fn() })
      renderHeader()
      // The moon icon is shown by default (dark = false)
      const toggle = document.querySelector('.p-2.rounded-lg') // last one is the theme toggle
      expect(toggle).toBeTruthy()
    })

    it('toggles between moon and sun icons', () => {
      mockUseAuth.mockReturnValue({ user: null, loading: false, signInWithGoogle: vi.fn(), signOut: vi.fn() })
      const { container } = renderHeader()
      // Initially dark=false, so Moon icon is shown
      const moonIcon = container.querySelector('.lucide-moon')
      expect(moonIcon).toBeTruthy()

      // Click the theme toggle button (last button with the right class pattern)
      const buttons = container.querySelectorAll('button.p-2.rounded-lg')
      const themeToggle = buttons[buttons.length - 1]
      fireEvent.click(themeToggle)

      // After toggle, dark=true, Sun icon should appear
      const sunIcon = container.querySelector('.lucide-sun')
      expect(sunIcon).toBeTruthy()
    })

    it('persists theme preference to localStorage', () => {
      mockUseAuth.mockReturnValue({ user: null, loading: false, signInWithGoogle: vi.fn(), signOut: vi.fn() })
      const { container } = renderHeader()

      const themeToggle = container.querySelectorAll('button.p-2.rounded-lg')[1] || container.querySelector('button.p-2.rounded-lg')
      if (themeToggle) {
        fireEvent.click(themeToggle)
      }

      expect(localStorageMock.setItem).toHaveBeenCalledWith('theme', expect.any(String))
    })

    it('reads initial theme from localStorage when dark', () => {
      localStorageMock.setItem('theme', 'dark')
      mockUseAuth.mockReturnValue({ user: null, loading: false, signInWithGoogle: vi.fn(), signOut: vi.fn() })
      const { container } = renderHeader()
      const sunIcon = container.querySelector('.lucide-sun')
      expect(sunIcon).toBeTruthy()
    })
  })
})
