import { Routes, Route, Link } from 'react-router-dom'
import { lazy, Suspense } from 'react'
import Header from './components/Header'
import Loading from './components/Loading'
import { useAuth } from './lib/AuthContext'

const Home = lazy(() => import('./pages/Home'))
const StockDetail = lazy(() => import('./pages/StockDetail'))
const Watchlist = lazy(() => import('./pages/Watchlist'))
const Universe = lazy(() => import('./pages/Universe'))
const Battle = lazy(() => import('./pages/Battle'))
const AuthCallback = lazy(() => import('./pages/AuthCallback'))

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

function LoginGate({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()

  if (loading) return <Loading />

  if (!user) {
    return (
      <div className="flex items-center justify-center py-32">
        <p className="text-gray-500 text-lg">Sign in to manage your portfolio</p>
      </div>
    )
  }

  return <>{children}</>
}

export default function App() {
  return (
    <Suspense fallback={<Loading />}>
      <Routes>
        <Route path="/auth/callback" element={<AuthCallback />} />
        <Route path="*" element={
          <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
            <Header />
            <LoginGate>
              <Routes>
                <Route path="/" element={<Home />} />
                <Route path="/stock/:code" element={<StockDetail />} />
                <Route path="/watchlist" element={<Watchlist />} />
                <Route path="/universe" element={<Universe />} />
                <Route path="/battle" element={<Battle />} />
                <Route path="*" element={<NotFound />} />
              </Routes>
            </LoginGate>
          </div>
        } />
      </Routes>
    </Suspense>
  )
}
