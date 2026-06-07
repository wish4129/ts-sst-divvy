import { describe, it, expect, vi } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import { ToastProvider, useToast } from '../../contexts/ToastContext'

function Consumer() {
  const { toasts, addToast, removeToast } = useToast()
  return (
    <div>
      <span data-testid="count">{toasts.length}</span>
      <button onClick={() => addToast('Test message', 'success')}>Add Toast</button>
      <button onClick={() => addToast('Warning', 'warning')}>Add Warning</button>
      {toasts.map(t => (
        <button key={t.id} onClick={() => removeToast(t.id)}>Dismiss {t.id}</button>
      ))}
    </div>
  )
}

describe('ToastContext', () => {
  it('provides empty toast array initially', () => {
    render(
      <ToastProvider>
        <Consumer />
      </ToastProvider>
    )
    expect(screen.getByTestId('count').textContent).toBe('0')
  })

  it('adds toast on addToast call', () => {
    render(
      <ToastProvider>
        <Consumer />
      </ToastProvider>
    )
    act(() => {
      screen.getByText('Add Toast').click()
    })
    expect(screen.getByTestId('count').textContent).toBe('1')
    // Toast data is in context — dismiss button shows toast ID
    expect(screen.getByText(/dismiss/i)).toBeTruthy()
  })

  it('removes toast on removeToast call', () => {
    render(
      <ToastProvider>
        <Consumer />
      </ToastProvider>
    )
    act(() => {
      screen.getByText('Add Toast').click()
    })
    const dismissBtn = screen.getByText(/dismiss/i)
    act(() => {
      dismissBtn.click()
    })
    expect(screen.getByTestId('count').textContent).toBe('0')
  })

  it('supports multiple toast types', () => {
    render(
      <ToastProvider>
        <Consumer />
      </ToastProvider>
    )
    act(() => {
      screen.getByText('Add Toast').click()
      screen.getByText('Add Warning').click()
    })
    expect(screen.getByTestId('count').textContent).toBe('2')
  })

  it('throws when useToast used outside provider', () => {
    // Suppress console.error for expected error
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    expect(() => render(<Consumer />)).toThrow('useToast must be used within ToastProvider')
    spy.mockRestore()
  })
})
