import { useState, useEffect, useCallback, useRef } from 'react'

const API_URL = import.meta.env.VITE_API_URL || ''

export interface ApiState<T> {
  data: T | null
  loading: boolean
  error: string | null
  refetch: () => void
}

/**
 * Generic data-fetching hook. Returns { data, loading, error, refetch }.
 * Pass null as url to skip fetching (e.g., API_URL not available).
 * Auto-retries once on failure after 1s delay.
 */
export function useApi<T>(url: string | null, options?: { retries?: number }): ApiState<T> {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const retries = options?.retries ?? 1
  const attemptRef = useRef(0)
  const mountedRef = useRef(true)

  const fetchData = useCallback(async (attempt: number = 0) => {
    if (!url) {
      setLoading(false)
      return
    }

    setLoading(true)
    setError(null)

    try {
      const fullUrl = url.startsWith('http') ? url : `${API_URL}${url}`
      const res = await fetch(fullUrl)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const json = await res.json()
      if (mountedRef.current) {
        setData(json)
        setError(null)
      }
    } catch (e: any) {
      if (!mountedRef.current) return
      if (attempt < retries) {
        attemptRef.current = attempt + 1
        setTimeout(() => fetchData(attempt + 1), 1000)
        return
      }
      setError(e?.message || 'Failed to load data')
    } finally {
      if (mountedRef.current) {
        setLoading(false)
      }
    }
  }, [url, retries])

  useEffect(() => {
    mountedRef.current = true
    fetchData()
    return () => { mountedRef.current = false }
  }, [fetchData])

  const refetch = useCallback(() => {
    attemptRef.current = 0
    fetchData(0)
  }, [fetchData])

  return { data, loading, error, refetch }
}

/**
 * JSON-only POST helper. Returns { data, loading, error, refetch }.
 */
export function useApiPost<T, B = unknown>(url: string | null, body: B): ApiState<T> {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = useCallback(async () => {
    if (!url) { setLoading(false); return }
    setLoading(true)
    setError(null)

    try {
      const fullUrl = url.startsWith('http') ? url : `${API_URL}${url}`
      const res = await fetch(fullUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const json = await res.json()
      setData(json)
    } catch (e: any) {
      setError(e?.message || 'Failed to post data')
    } finally {
      setLoading(false)
    }
  }, [url, JSON.stringify(body)])

  useEffect(() => { fetchData() }, [fetchData])

  return { data, loading, error, refetch: fetchData }
}
