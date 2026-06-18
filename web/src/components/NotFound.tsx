import { useEffect } from 'react'
import { Link } from 'react-router-dom'

export default function NotFound() {
  useEffect(() => {
    // Add noindex meta tag to prevent Google from indexing
    // SPA fallback (HTTP 200) pages for non-existent routes
    let meta = document.querySelector('meta[name="robots"]')
    if (!meta) {
      meta = document.createElement('meta')
      meta.setAttribute('name', 'robots')
      document.head.appendChild(meta)
    }
    meta.setAttribute('content', 'noindex')
    return () => {
      // Remove on unmount so real pages aren't affected
      meta?.remove()
    }
  }, [])

  return (
    <div role="alert" className="flex flex-col items-center justify-center min-h-[60vh] gap-6 px-4 text-center">
      <div className="flex flex-col items-center gap-2">
        <span className="text-7xl font-bold text-gray-200 dark:text-gray-800 select-none">404</span>
        <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
          Page not found
        </h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 max-w-md">
          This page doesn't exist or has been moved. Double-check the URL or head back.
        </p>
      </div>
      <div className="flex gap-3">
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-emerald-600 text-white text-sm font-medium hover:bg-emerald-700 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-4 0h4" />
          </svg>
          Back to Dashboard
        </Link>
        <Link
          to="/universe"
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
        >
          Browse Stocks
        </Link>
      </div>
    </div>
  )
}
