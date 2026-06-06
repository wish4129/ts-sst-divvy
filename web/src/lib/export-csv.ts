/**
 * Utility to export watchlist data as CSV and trigger download.
 */
export interface CsvRow {
  code: string
  name: string
  industry: string
  lastPrice: number
  dividendYield: number
  pe: number
  score: number
  status: string
  hasAiReport: boolean
}

function escapeCsvField(val: string | number): string {
  const s = String(val)
  if (s.includes(',') || s.includes('"') || s.includes('\n')) {
    return `"${s.replace(/"/g, '""')}"`
  }
  return s
}

export function stocksToCsv(rows: CsvRow[]): string {
  const headers = ['Code', 'Name', 'Industry', 'Last Price (RM)', 'D/Y (%)', 'P/E', 'Score', 'Status', 'Has AI Report']
  const lines = [headers.join(',')]

  for (const r of rows) {
    lines.push([
      escapeCsvField(r.code),
      escapeCsvField(r.name),
      escapeCsvField(r.industry),
      r.lastPrice.toFixed(2),
      r.dividendYield.toFixed(2),
      r.pe > 0 ? r.pe.toFixed(1) : '',
      r.score.toString(),
      r.status,
      r.hasAiReport ? 'Yes' : 'No',
    ].join(','))
  }

  return lines.join('\n')
}

export function downloadCsv(rows: CsvRow[], filename?: string) {
  const csv = stocksToCsv(rows)
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)

  const a = document.createElement('a')
  a.href = url
  a.download = filename || `divvy-watchlist-${new Date().toISOString().slice(0, 10)}.csv`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
