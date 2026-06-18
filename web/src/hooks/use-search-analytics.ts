import { useRef, useCallback } from 'react'

const SESSION_KEY = 'divvy_session_id'
const SESSION_EXPIRY_MS = 30 * 60 * 1000 // 30 minutes

function getSessionId(): string | null {
  try {
    const raw = localStorage.getItem(SESSION_KEY)
    if (raw) {
      const { id, expires } = JSON.parse(raw)
      if (Date.now() < expires) return id
    }
    const id = crypto.randomUUID()
    localStorage.setItem(SESSION_KEY, JSON.stringify({
      id,
      expires: Date.now() + SESSION_EXPIRY_MS,
    }))
    return id
  } catch {
    return null
  }
}

/**
 * Log search queries to the backend analytics endpoint.
 * Fire-and-forget — never blocks search UX.
 */
export function useSearchAnalytics() {
  const sessionId = useRef(getSessionId())
  const API_URL = import.meta.env.VITE_API_URL || ''

  const logSearch = useCallback((query: string, resultCount: number) => {
    if (!query.trim() || !API_URL) return
    fetch(`${API_URL}/universe/search-log`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query: query.trim(),
        resultCount,
        sessionId: sessionId.current,
      }),
    }).catch(() => {
      // Fire-and-forget
    })
  }, [API_URL])

  return { logSearch }
}
