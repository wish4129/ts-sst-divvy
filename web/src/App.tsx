import { Routes, Route } from 'react-router-dom'
import { lazy, Suspense } from 'react'
import Header from './components/Header'
import Loading from './components/Loading'
import LoginGate from './components/LoginGate'
import NotFound from './components/NotFound'

const Home = lazy(() => import('./pages/Home'))
const StockDetail = lazy(() => import('./pages/StockDetail'))
const Watchlist = lazy(() => import('./pages/Watchlist'))
const Universe = lazy(() => import('./pages/Universe'))
const Battle = lazy(() => import('./pages/Battle'))
const AuthCallback = lazy(() => import('./pages/AuthCallback'))

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
