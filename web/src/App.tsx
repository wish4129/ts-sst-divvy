import { Routes, Route, Link } from 'react-router-dom'
import { lazy, Suspense } from 'react'
import Header from './components/Header'
import { useAuth } from './lib/AuthContext'

const Home = lazy(() => import('./pages/Home'))
const StockDetail = lazy(() => import('./pages/StockDetail'))
const Watchlist = lazy(() => import('./pages/Watchlist'))
const Battle = lazy(() => import('./pages/Battle'))
const AuthCallback = lazy(() => import('./pages/AuthCallback'))

function Loading() {
  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600" />
    </div>
  )
}

function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen gap-4">
      <h1 className="text-4xl font-bold text-gray-300 dark:text-gray-700">404</h1>
      <p className="text-gray-500">Page not found</p>
      <Link to="/" className="text-emerald-600 hover:text-emerald-700 font-medium">
        Back to Dashboard
      </Link>
    </div>
  )
}

function LoginGate() {
  const { user, loading, signInWithGoogle } = useAuth()

  if (loading) return <Loading />

  if (!user) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-6">
        <h1 className="text-2xl font-bold text-gray-800 dark:text-gray-200">Divvy</h1>
        <p className="text-gray-500">Sign in to manage your portfolio</p>
        <button
          onClick={signInWithGoogle}
          className="flex items-center gap-2 px-6 py-3 rounded-lg font-medium bg-emerald-600 text-white hover:bg-emerald-700 transition-colors"
        >
          Sign in with Google
        </button>
      </div>
    )
  }

  return null
}

export default function App() {
  return (
    <Suspense fallback={<Loading />}>
      <Routes>
        {/* Auth callback — no header/gate */}
        <Route path="/auth/callback" element={<AuthCallback />} />

        {/* All other routes — gated behind login */}
        <Route path="*" element={
          <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
            <Header />
            <LoginGate />
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/stock/:code" element={<StockDetail />} />
              <Route path="/watchlist" element={<Watchlist />} />
              <Route path="/battle" element={<Battle />} />
              <Route path="*" element={<NotFound />} />
            </Routes>
          </div>
        } />
      </Routes>
    </Suspense>
  )
}
