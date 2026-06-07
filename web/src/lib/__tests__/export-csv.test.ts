import { describe, it, expect, vi, beforeEach } from 'vitest'
import { downloadCsv, type CsvRow } from '../export-csv'

describe('export-csv', () => {
  beforeEach(() => {
    // Mock URL.createObjectURL and anchor click
    global.URL.createObjectURL = vi.fn(() => 'blob:test')
    global.URL.revokeObjectURL = vi.fn()
  })

  it('generates CSV with headers', () => {
    const rows: CsvRow[] = [
      { code: 'MAYBANK', name: 'Maybank', industry: 'Banking', lastPrice: 10.50, dividendYield: 5.2, pe: 12.5, score: 85, status: 'active', hasAiReport: true },
    ]
    const createElementSpy = vi.spyOn(document, 'createElement')
    downloadCsv(rows)
    
    const anchor = createElementSpy.mock.results.find(r => r.value instanceof HTMLAnchorElement)?.value
    expect(anchor).toBeTruthy()
    const blobUrl = anchor?.href
    expect(blobUrl).toBe('blob:test')
  })

  it('includes header row', () => {
    const rows: CsvRow[] = [{ code: 'TEST', name: 'Test', industry: 'Tech', lastPrice: 1.0, dividendYield: 0, pe: 10, score: 50, status: 'active', hasAiReport: false }]
    
    const appendChildSpy = vi.spyOn(document.body, 'appendChild')
    downloadCsv(rows)
    
    expect(appendChildSpy).toHaveBeenCalled()
    const anchor = appendChildSpy.mock.calls[0][0] as HTMLAnchorElement
    expect(anchor.download).toContain('.csv')
  })

  it('handles empty rows gracefully', () => {
    expect(() => downloadCsv([])).not.toThrow()
  })

  it('handles null values with empty strings', () => {
    const rows: CsvRow[] = [
      { code: 'TEST', name: 'Test', industry: 'Tech', lastPrice: 0, dividendYield: 0, pe: 0, score: 0, status: 'revisit', hasAiReport: false },
    ]
    expect(() => downloadCsv(rows)).not.toThrow()
  })
})
