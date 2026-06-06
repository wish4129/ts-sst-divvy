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
const Compare = lazy(() => import('./pages/Compare'))
const DividendCalendar = lazy(() => import('./pages/DividendCalendar'))
const Screener = lazy(() => import('./pages/Screener'))
const AuthCallback = lazy(() => import('./pages/AuthCallback'))

function Page({ children }: { children: React.ReactNode }) {
  return (
    <ErrorBoundary>
      <div className="page-enter">{children}</div>
    </ErrorBoundary>
  )
}

export default function App() {
  return (
    <Suspense fallback={<Loading />}>
      <Routes>
        <Route path="/auth/callback" element={<AuthCallback />} />
        <Route path="*" element={
          <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
            <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-emerald-600 focus:text-white focus:rounded-lg focus:shadow-lg focus:outline-none focus:ring-2 focus:ring-emerald-400">
              Skip to main content
            </a>
            <Header />
            <main id="main-content" tabIndex={-1}>
              <LoginGate>
                <Routes>
                  <Route path="/" element={<Page><Home /></Page>} />
                  <Route path="/stock/:code" element={<Page><StockDetail /></Page>} />
                  <Route path="/watchlist" element={<Page><Watchlist /></Page>} />
                  <Route path="/universe" element={<Page><Universe /></Page>} />
                  <Route path="/battle" element={<Page><Battle /></Page>} />
                  <Route path="/compare" element={<Page><Compare /></Page>} />
                  <Route path="/dividends" element={<Page><DividendCalendar /></Page>} />
                  <Route path="/screener" element={<Page><Screener /></Page>} />
                  <Route path="*" element={<NotFound />} />
                </Routes>
              </LoginGate>
            </main>
          </div>
        } />
      </Routes>
    </Suspense>
  )
}
