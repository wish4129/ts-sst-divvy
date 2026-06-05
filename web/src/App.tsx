import { Routes, Route } from 'react-router-dom'
import { lazy, Suspense } from 'react'
import Header from './components/Header'
import Loading from './components/Loading'
import NotFound from './components/NotFound'
import { useAuth } from './lib/AuthContext'

const Home = lazy(() => import('./pages/Home'))
const StockDetail = lazy(() => import('./pages/StockDetail'))
const Watchlist = lazy(() => import('./pages/Watchlist'))
const Universe = lazy(() => import('./pages/Universe'))
const Battle = lazy(() => import('./pages/Battle'))
const AuthCallback = lazy(() => import('./pages/AuthCallback'))

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
