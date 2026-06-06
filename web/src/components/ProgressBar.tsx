import { useEffect, useRef } from 'react'

export default function ProgressBar() {
  const barRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const bar = barRef.current
    if (!bar) return

    // Start the bar after first paint
    const raf = requestAnimationFrame(() => {
      bar.style.width = '85%'
    })

    return () => {
      cancelAnimationFrame(raf)
      // On unmount: rush to 100% and fade out
      if (bar) {
        bar.style.transition = 'width 0.3s ease-out, opacity 0.4s ease-out'
        bar.style.width = '100%'
        bar.style.opacity = '0'
      }
    }
  }, [])

  return (
    <div
      className="fixed top-0 left-0 right-0 z-50 pointer-events-none"
      aria-hidden="true"
    >
      <div
        ref={barRef}
        className="h-0.5 bg-gradient-to-r from-emerald-400 via-emerald-500 to-emerald-300"
        style={{
          width: '0%',
          transition: 'width 8s cubic-bezier(0.1, 0.05, 0, 1)',
          boxShadow: '0 0 10px rgba(16, 185, 129, 0.6)',
        }}
      />
    </div>
  )
}
