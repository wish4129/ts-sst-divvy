import { Routes, Route } from 'react-router-dom'
import { lazy, Suspense } from 'react'
import Header from './components/Header'
import Loading from './components/Loading'
import LoginGate from './components/LoginGate'
import NotFound from './components/NotFound'
import ErrorBoundary from './components/ErrorBoundary'

const Home = lazy(() => import('./pages/Home'))
const StockDetail = lazy(() => import('./pages/StockDetail'))
const Watchlist = lazy(() => import('./pages/Watchlist'))
const Universe = lazy(() => import('./pages/Universe'))
const Battle = lazy(() => import('./pages/Battle'))
const AuthCallback = lazy(() => import('./pages/AuthCallback'))

function Page({ children }: { children: React.ReactNode }) {
  return <ErrorBoundary>{children}</ErrorBoundary>
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
                <Route path="/" element={<Page><Home /></Page>} />
                <Route path="/stock/:code" element={<Page><StockDetail /></Page>} />
                <Route path="/watchlist" element={<Page><Watchlist /></Page>} />
                <Route path="/universe" element={<Page><Universe /></Page>} />
                <Route path="/battle" element={<Page><Battle /></Page>} />
                <Route path="*" element={<NotFound />} />
              </Routes>
            </LoginGate>
          </div>
        } />
      </Routes>
    </Suspense>
  )
}
