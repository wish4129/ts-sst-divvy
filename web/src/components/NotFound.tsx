import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <div role="alert" className="flex flex-col items-center justify-center min-h-screen gap-4">
      <h1 className="text-4xl font-bold text-gray-300 dark:text-gray-700">404</h1>
      <p className="text-gray-500">Page not found</p>
      <Link to="/" className="text-emerald-600 hover:text-emerald-700 font-medium">
        Back to Dashboard
      </Link>
    </div>
  )
}
