interface ScoreBadgeProps {
  score: number
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

export default function ScoreBadge({ score, size = 'md', className = '' }: ScoreBadgeProps) {
  const dims = { sm: 40, md: 56, lg: 72 }
  const fonts = { sm: 'text-xs', md: 'text-sm', lg: 'text-lg' }
  const d = dims[size]
  const r = d / 2 - 4
  const circumference = 2 * Math.PI * r
  const offset = circumference - (score / 100) * circumference

  const color = score >= 70
    ? 'stroke-emerald-500 text-emerald-700 dark:text-emerald-400'
    : score >= 50
    ? 'stroke-amber-500 text-amber-700 dark:text-amber-400'
    : 'stroke-red-500 text-red-700 dark:text-red-400'

  return (
    <div className={`relative inline-flex items-center justify-center ${className}`} role="img" aria-label={`Score: ${score} out of 100`}>
      <svg width={d} height={d} className="-rotate-90">
        <circle cx={d / 2} cy={d / 2} r={r} fill="none" className="stroke-gray-200 dark:stroke-gray-700" strokeWidth="3" />
        <circle
          cx={d / 2} cy={d / 2} r={r} fill="none" className={color}
          strokeWidth="3" strokeLinecap="round"
          strokeDasharray={circumference} strokeDashoffset={offset}
          style={{ transition: 'stroke-dashoffset 0.5s ease' }}
        />
      </svg>
      <span className={`absolute font-bold ${fonts[size]} ${color.split(' ')[1]}`}>{score}</span>
    </div>
  )
}
