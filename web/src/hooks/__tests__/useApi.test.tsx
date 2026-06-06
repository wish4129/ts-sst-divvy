import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { useApi, useApiPost } from '../useApi'

// Mock fetch globally
const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

const BASE = 'https://api.example.com'

beforeEach(() => {
  mockFetch.mockReset()
  mockFetch.mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => ({ items: [1, 2, 3] }),
  })
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('useApi', () => {
  it('returns loading=true initially', () => {
    const { result } = renderHook(() => useApi(`${BASE}/test`))
    expect(result.current.loading).toBe(true)
    expect(result.current.data).toBeNull()
    expect(result.current.error).toBeNull()
  })

  it('fetches data and returns it', async () => {
    const { result } = renderHook(() => useApi(`${BASE}/test`))
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.data).toEqual({ items: [1, 2, 3] })
    expect(result.current.error).toBeNull()
  })

  it('returns error when fetch fails', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => ({}),
    })
    const { result } = renderHook(() => useApi(`${BASE}/fail`, { retries: 0 }))
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.error).toBe('HTTP 500')
    expect(result.current.data).toBeNull()
  })

  it('returns error when fetch throws', async () => {
    mockFetch.mockRejectedValueOnce(new Error('Network error'))
    const { result } = renderHook(() => useApi(`${BASE}/throw`, { retries: 0 }))
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.error).toBe('Network error')
  })

  it('skips fetch when url is null', () => {
    const { result } = renderHook(() => useApi(null))
    expect(result.current.loading).toBe(false)
    expect(result.current.data).toBeNull()
  })

  it('refetch re-triggers the request', async () => {
    mockFetch
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ first: true }) })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ second: true }) })

    const { result } = renderHook(() => useApi(`${BASE}/refetch`))
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.data).toEqual({ first: true })

    result.current.refetch()
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.data).toEqual({ second: true })
  })
})

describe('useApiPost', () => {
  it('sends POST with JSON body', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ success: true }),
    })
    const { result } = renderHook(() => useApiPost(`${BASE}/post`, { name: 'test' }))
    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(mockFetch).toHaveBeenCalledWith(
      `${BASE}/post`,
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: 'test' }),
      })
    )
    expect(result.current.data).toEqual({ success: true })
  })

  it('returns error on failed POST', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: async () => ({}),
    })
    const { result } = renderHook(() => useApiPost(`${BASE}/post`, {}))
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.error).toBe('HTTP 400')
  })
})
