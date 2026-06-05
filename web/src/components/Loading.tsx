export default function Loading() {
  return (
    <div className="flex items-center justify-center min-h-screen">
      <div
        className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600"
        role="status"
        aria-label="Loading"
      >
        <span className="sr-only">Loading...</span>
      </div>
    </div>
  )
}
