import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent, act } from '@testing-library/react'
import { ToastProvider, useToast } from '../../contexts/ToastContext'
import ToastContainer from '../Toast'

function ToastTrigger({ message, type = 'info' as const }: { message: string; type?: 'success' | 'error' | 'info' | 'warning' }) {
  const { addToast } = useToast()
  return <button onClick={() => addToast(message, type)}>Show Toast</button>
}

function renderToast(message: string, type?: 'success' | 'error' | 'info' | 'warning') {
  return render(
    <ToastProvider>
      <ToastContainer />
      <ToastTrigger message={message} type={type} />
    </ToastProvider>
  )
}

describe('Toast', () => {
  it('renders nothing when no toasts', () => {
    const { container } = render(
      <ToastProvider>
        <ToastContainer />
      </ToastProvider>
    )
    expect(container.firstElementChild).toBeNull()
  })

  it('shows success toast with message', () => {
    renderToast('Saved successfully!', 'success')
    act(() => {
      fireEvent.click(screen.getByText('Show Toast'))
    })
    expect(screen.getByText('Saved successfully!')).toBeTruthy()
  })

  it('shows error toast', () => {
    renderToast('Something went wrong', 'error')
    act(() => {
      fireEvent.click(screen.getByText('Show Toast'))
    })
    expect(screen.getByText('Something went wrong')).toBeTruthy()
  })

  it('shows info toast by default', () => {
    renderToast('Just an FYI')
    act(() => {
      fireEvent.click(screen.getByText('Show Toast'))
    })
    expect(screen.getByText('Just an FYI')).toBeTruthy()
  })

  it('shows warning toast', () => {
    renderToast('Heads up!', 'warning')
    act(() => {
      fireEvent.click(screen.getByText('Show Toast'))
    })
    expect(screen.getByText('Heads up!')).toBeTruthy()
  })

  it('has dismiss button', () => {
    renderToast('Dismiss me')
    act(() => {
      fireEvent.click(screen.getByText('Show Toast'))
    })
    expect(screen.getByLabelText('Dismiss notification')).toBeTruthy()
  })

  it('has live region for accessibility', () => {
    renderToast('Test')
    act(() => {
      fireEvent.click(screen.getByText('Show Toast'))
    })
    const container = screen.getByLabelText('Notifications')
    expect(container.getAttribute('aria-live')).toBe('polite')
  })

  it('renders toast with role alert', () => {
    renderToast('Alert!', 'error')
    act(() => {
      fireEvent.click(screen.getByText('Show Toast'))
    })
    expect(screen.getByRole('alert')).toBeTruthy()
  })
})
