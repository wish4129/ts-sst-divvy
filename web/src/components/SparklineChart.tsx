interface SparklineChartProps {
  data: number[]
  width?: number
  height?: number
  color?: string
}

export default function SparklineChart({ data, width = 80, height = 30, color = '#059669' }: SparklineChartProps) {
  if (!data.length) return null

  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min || 1
  const pad = 2

  const points = data.map((v, i) => {
    const x = pad + (i / (data.length - 1)) * (width - pad * 2)
    const y = height - pad - ((v - min) / range) * (height - pad * 2)
    return `${x},${y}`
  }).join(' ')

  const lastY = height - pad - ((data[data.length - 1] - min) / range) * (height - pad * 2)
  const firstY = height - pad - ((data[0] - min) / range) * (height - pad * 2)
  const trend = data[data.length - 1] >= data[0] ? color : '#ef4444'

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} className="w-full h-auto flex-shrink-0" preserveAspectRatio="xMidYMid meet">
      <defs>
        <linearGradient id={`spark-${data[0]}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={trend} stopOpacity="0.3" />
          <stop offset="100%" stopColor={trend} stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon
        points={`${pad},${height - pad} ${points} ${width - pad},${height - pad}`}
        fill={`url(#spark-${data[0]})`}
      />
      <polyline points={points} fill="none" stroke={trend} strokeWidth="1.5" strokeLinejoin="round" />
    </svg>
  )
}
