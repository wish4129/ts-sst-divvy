import { useRef, useEffect, useState } from 'react'

interface SparklineChartProps {
  data: number[]
  width?: number
  height?: number
  color?: string
}

export default function SparklineChart({ data, width, height = 30, color = '#059669' }: SparklineChartProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [chartWidth, setChartWidth] = useState(width ?? 80)
  const [initialized, setInitialized] = useState(false)

  useEffect(() => {
    if (width !== undefined) return // fixed width, no auto-sizing needed
    const container = containerRef.current
    if (!container) return

    const measure = () => {
      const w = container.clientWidth
      if (w > 0) {
        setChartWidth(w)
        setInitialized(true)
      }
    }

    measure()

    const observer = new ResizeObserver(measure)
    observer.observe(container)
    return () => observer.disconnect()
  }, [width])

  // When width is 0 explicitly, wait for resize measurement
  if (!data.length) return null

  const renderWidth = width ?? chartWidth
  const renderHeight = height
  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min || 1
  const pad = 2

  const points = data.map((v, i) => {
    const x = pad + (i / (data.length - 1)) * (renderWidth - pad * 2)
    const y = renderHeight - pad - ((v - min) / range) * (renderHeight - pad * 2)
    return `${x},${y}`
  }).join(' ')

  const trend = data[data.length - 1] >= data[0] ? color : '#ef4444'

  const svg = (
    <svg
      width={renderWidth}
      height={renderHeight}
      viewBox={`0 0 ${renderWidth} ${renderHeight}`}
      className="w-full h-auto flex-shrink-0"
      preserveAspectRatio="xMidYMid meet"
    >
      <defs>
        <linearGradient id={`spark-${data[0]}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={trend} stopOpacity="0.3" />
          <stop offset="100%" stopColor={trend} stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon
        points={`${pad},${renderHeight - pad} ${points} ${renderWidth - pad},${renderHeight - pad}`}
        fill={`url(#spark-${data[0]})`}
      />
      <polyline points={points} fill="none" stroke={trend} strokeWidth="1.5" strokeLinejoin="round" />
    </svg>
  )

  if (width !== undefined) return svg

  return (
    <div ref={containerRef} className="w-full">
      {!initialized ? (
        <svg width={80} height={renderHeight} viewBox={`0 0 80 ${renderHeight}`} className="w-full h-auto flex-shrink-0 opacity-0" preserveAspectRatio="xMidYMid meet">
          <polyline points="" fill="none" stroke="transparent" strokeWidth="1.5" />
        </svg>
      ) : svg}
    </div>
  )
}
