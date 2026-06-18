import { Routes, Route, Link } from 'react-router-dom'
import { lazy, Suspense } from 'react'
import Header from './components/Header'
import Loading from './components/Loading'
import ProgressBar from './components/ProgressBar'
import ToastContainer from './components/Toast'
import { ToastProvider } from './contexts/ToastContext'
import LoginGate from './components/LoginGate'
import NotFound from './components/NotFound'
import ErrorBoundary from './components/ErrorBoundary'

const Home = lazy(() => import('./pages/Home'))
const StockDetail = lazy(() => import('./pages/StockDetail'))
const Watchlist = lazy(() => import('./pages/Watchlist'))
const Universe = lazy(() => import('./pages/Universe'))
const Compare = lazy(() => import('./pages/Compare'))
const DividendCalendar = lazy(() => import('./pages/DividendCalendar'))
const Screener = lazy(() => import('./pages/Screener'))
const Analytics = lazy(() => import('./pages/Analytics'))
const Blog = lazy(() => import('./pages/Blog'))
const BlogPost = lazy(() => import('./pages/BlogPost'))
const AuthCallback = lazy(() => import('./pages/AuthCallback'))
const Privacy = lazy(() => import('./pages/Privacy'))
const Disclaimer = lazy(() => import('./pages/Disclaimer'))
const Terms = lazy(() => import('./pages/Terms'))

function Page({ children }: { children: React.ReactNode }) {
  return (
    <ErrorBoundary>
      <div className="page-enter">{children}</div>
    </ErrorBoundary>
  )
}

/** App shell: header, footer, auth gate, and nested routes */
function AppShell() {
  return (
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
            <Route path="/compare" element={<Page><Compare /></Page>} />
            <Route path="/dividends" element={<Page><DividendCalendar /></Page>} />
            <Route path="/screener" element={<Page><Screener /></Page>} />
            <Route path="/analytics" element={<Page><Analytics /></Page>} />
          </Routes>
        </LoginGate>
      </main>
      <footer className="border-t border-gray-200 dark:border-gray-800 py-4 px-4">
        <div className="max-w-7xl mx-auto flex justify-center gap-6 text-xs text-gray-400 dark:text-gray-500">
          <Link to="/disclaimer" className="hover:text-gray-600 dark:hover:text-gray-300">Disclaimer</Link>
          <Link to="/privacy" className="hover:text-gray-600 dark:hover:text-gray-300">Privacy</Link>
          <Link to="/terms" className="hover:text-gray-600 dark:hover:text-gray-300">Terms</Link>
        </div>
      </footer>
      <ToastContainer />
    </div>
  )
}

export default function App() {
  return (
    <ToastProvider>
    <Suspense fallback={<><ProgressBar /><Loading /></>}>
      <Routes>
        {/* Public pages (no header/auth shell) */}
        <Route path="/auth/callback" element={<AuthCallback />} />
        <Route path="/blog" element={<Page><Blog /></Page>} />
        <Route path="/blog/:slug" element={<Page><BlogPost /></Page>} />
        <Route path="/privacy" element={<Page><Privacy /></Page>} />
        <Route path="/disclaimer" element={<Page><Disclaimer /></Page>} />
        <Route path="/terms" element={<Page><Terms /></Page>} />

        {/* Auth-required pages in the app shell */}
        <Route path="/" element={<AppShell />} />
        <Route path="/stock/:code" element={<AppShell />} />
        <Route path="/watchlist" element={<AppShell />} />
        <Route path="/universe" element={<AppShell />} />
        <Route path="/compare" element={<AppShell />} />
        <Route path="/dividends" element={<AppShell />} />
        <Route path="/screener" element={<AppShell />} />
        <Route path="/analytics" element={<AppShell />} />

        {/* 404 — no auth required */}
        <Route path="/battle" element={<Page><NotFound /></Page>} />
        <Route path="*" element={<Page><NotFound /></Page>} />
      </Routes>
    </Suspense>
    </ToastProvider>
  )
}
