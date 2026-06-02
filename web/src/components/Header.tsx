import { Link, useLocation } from 'react-router-dom'
import { LayoutDashboard, List, Swords, Sun, Moon, LogIn, LogOut, User, Globe } from 'lucide-react'
import { useState, useEffect } from 'react'
import { useAuth } from '../lib/AuthContext'

export default function Header() {
  const location = useLocation()
  const { user, loading, signInWithGoogle, signOut } = useAuth()
  const [dark, setDark] = useState(() => {
    if (typeof window === 'undefined') return false
    return localStorage.getItem('theme') === 'dark' ||
      (!localStorage.getItem('theme') && window.matchMedia('(prefers-color-scheme: dark)').matches)
  })

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
    localStorage.setItem('theme', dark ? 'dark' : 'light')
  }, [dark])

  const linkClass = (path: string) =>
    `flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
      location.pathname === path
        ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300'
        : 'text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100'
    }`

  return (
    <header className="border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950">
      <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between">
        <div className="flex items-center gap-6">
          <Link to="/" className="text-xl font-bold text-emerald-600 dark:text-emerald-400">
            Divvy
          </Link>
          <nav className="flex items-center gap-1">
            <Link to="/" className={linkClass('/')}>
              <LayoutDashboard className="w-4 h-4" />
              <span className="hidden sm:inline">Dashboard</span>
            </Link>
            <Link to="/watchlist" className={linkClass('/watchlist')}>
              <List className="w-4 h-4" />
              <span className="hidden sm:inline">Watchlist</span>
            </Link>
            <Link to="/universe" className={linkClass('/universe')}>
              <Globe className="w-4 h-4" />
              <span className="hidden sm:inline">Universe</span>
            </Link>
            <Link to="/battle" className={linkClass('/battle')}>
              <Swords className="w-4 h-4" />
              <span className="hidden sm:inline">Battle</span>
            </Link>
          </nav>
        </div>

        <div className="flex items-center gap-2">
          {loading ? (
            <div className="w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-700 animate-pulse" />
          ) : user ? (
            <div className="flex items-center gap-2">
              {user.user_metadata?.avatar_url ? (
                <img
                  src={user.user_metadata.avatar_url}
                  alt=""
                  className="w-7 h-7 rounded-full"
                />
              ) : (
                <div className="w-7 h-7 rounded-full bg-emerald-100 dark:bg-emerald-900 flex items-center justify-center">
                  <User className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                </div>
              )}
              <span className="hidden sm:inline text-sm text-gray-600 dark:text-gray-400 max-w-[120px] truncate">
                {user.user_metadata?.full_name || user.email}
              </span>
              <button
                onClick={signOut}
                className="p-2 rounded-lg text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800"
                title="Sign out"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <button
              onClick={signInWithGoogle}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium bg-emerald-600 text-white hover:bg-emerald-700 transition-colors"
            >
              <LogIn className="w-4 h-4" />
              <span className="hidden sm:inline">Sign in</span>
            </button>
          )}
          <button
            onClick={() => setDark(!dark)}
            className="p-2 rounded-lg text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800"
          >
            {dark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>
        </div>
      </div>
    </header>
  )
}
