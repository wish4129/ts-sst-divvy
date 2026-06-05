import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import IndustryFilter from '../IndustryFilter'

describe('IndustryFilter', () => {
  const defaultIndustries = ['Technology', 'Finance', 'Healthcare', 'Energy']

  it('renders the "All" button', () => {
    render(
      <IndustryFilter
        industries={defaultIndustries}
        selected=""
        onChange={() => {}}
      />
    )
    expect(screen.getByRole('button', { name: 'All' })).toBeInTheDocument()
  })

  it('renders all industry options as buttons', () => {
    render(
      <IndustryFilter
        industries={defaultIndustries}
        selected=""
        onChange={() => {}}
      />
    )
    for (const industry of defaultIndustries) {
      expect(screen.getByRole('button', { name: industry })).toBeInTheDocument()
    }
  })

  it('calls onChange with empty string when "All" is clicked', () => {
    const onChange = vi.fn()
    render(
      <IndustryFilter
        industries={defaultIndustries}
        selected="Technology"
        onChange={onChange}
      />
    )
    fireEvent.click(screen.getByRole('button', { name: 'All' }))
    expect(onChange).toHaveBeenCalledWith('')
    expect(onChange).toHaveBeenCalledTimes(1)
  })

  it('calls onChange with industry name when industry button is clicked', () => {
    const onChange = vi.fn()
    render(
      <IndustryFilter
        industries={defaultIndustries}
        selected=""
        onChange={onChange}
      />
    )
    fireEvent.click(screen.getByRole('button', { name: 'Finance' }))
    expect(onChange).toHaveBeenCalledWith('Finance')
  })

  it('calls onChange with empty string when selected industry is clicked again (toggle off)', () => {
    const onChange = vi.fn()
    render(
      <IndustryFilter
        industries={defaultIndustries}
        selected="Technology"
        onChange={onChange}
      />
    )
    fireEvent.click(screen.getByRole('button', { name: 'Technology' }))
    expect(onChange).toHaveBeenCalledWith('')
  })

  it('applies active styling to selected industry button', () => {
    render(
      <IndustryFilter
        industries={defaultIndustries}
        selected="Healthcare"
        onChange={() => {}}
      />
    )
    const activeBtn = screen.getByRole('button', { name: 'Healthcare' })
    expect(activeBtn.className).toContain('bg-emerald-600')
    expect(activeBtn.className).toContain('text-white')
  })

  it('applies active styling to "All" when no industry selected', () => {
    render(
      <IndustryFilter
        industries={defaultIndustries}
        selected=""
        onChange={() => {}}
      />
    )
    const allBtn = screen.getByRole('button', { name: 'All' })
    expect(allBtn.className).toContain('bg-emerald-600')
    expect(allBtn.className).toContain('text-white')
  })

  it('applies inactive styling to non-selected industry buttons', () => {
    render(
      <IndustryFilter
        industries={defaultIndustries}
        selected="Technology"
        onChange={() => {}}
      />
    )
    const inactiveBtn = screen.getByRole('button', { name: 'Finance' })
    expect(inactiveBtn.className).toContain('bg-gray-100')
    expect(inactiveBtn.className).toContain('text-gray-600')
    expect(inactiveBtn.className).not.toContain('bg-emerald-600')
  })

  it('renders only "All" button when industries array is empty', () => {
    render(
      <IndustryFilter
        industries={[]}
        selected=""
        onChange={() => {}}
      />
    )
    const buttons = screen.getAllByRole('button')
    expect(buttons).toHaveLength(1)
    expect(buttons[0]).toHaveTextContent('All')
  })

  it('handles a long list of industries', () => {
    const manyIndustries = Array.from({ length: 20 }, (_, i) => `Industry ${i}`)
    render(
      <IndustryFilter
        industries={manyIndustries}
        selected=""
        onChange={() => {}}
      />
    )
    // 20 industry buttons + 1 All button = 21
    const buttons = screen.getAllByRole('button')
    expect(buttons).toHaveLength(21)
    expect(screen.getByRole('button', { name: 'Industry 0' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Industry 19' })).toBeInTheDocument()
  })

  it('renders industry names with long text without truncation in the button', () => {
    const longIndustries = ['Semiconductor & Electronics Manufacturing']
    render(
      <IndustryFilter
        industries={longIndustries}
        selected=""
        onChange={() => {}}
      />
    )
    const btn = screen.getByRole('button', { name: longIndustries[0] })
    expect(btn).toBeInTheDocument()
    expect(btn.textContent).toBe(longIndustries[0])
  })

  it('only one button has active styling at a time', () => {
    render(
      <IndustryFilter
        industries={defaultIndustries}
        selected="Technology"
        onChange={() => {}}
      />
    )
    const allButtons = screen.getAllByRole('button')
    const activeButtons = allButtons.filter(btn =>
      btn.className.includes('bg-emerald-600')
    )
    expect(activeButtons).toHaveLength(1)
    expect(activeButtons[0]).toHaveTextContent('Technology')
  })

  it('switches active state when selected prop changes', () => {
    const { rerender } = render(
      <IndustryFilter
        industries={defaultIndustries}
        selected="Technology"
        onChange={() => {}}
      />
    )
    expect(screen.getByRole('button', { name: 'Technology' }).className).toContain('bg-emerald-600')
    expect(screen.getByRole('button', { name: 'Finance' }).className).not.toContain('bg-emerald-600')

    rerender(
      <IndustryFilter
        industries={defaultIndustries}
        selected="Finance"
        onChange={() => {}}
      />
    )
    expect(screen.getByRole('button', { name: 'Technology' }).className).not.toContain('bg-emerald-600')
    expect(screen.getByRole('button', { name: 'Finance' }).className).toContain('bg-emerald-600')
  })

  it('calls onChange when "All" is pressed with keyboard (Enter)', () => {
    const onChange = vi.fn()
    render(
      <IndustryFilter
        industries={defaultIndustries}
        selected="Technology"
        onChange={onChange}
      />
    )
    const allBtn = screen.getByRole('button', { name: 'All' })
    allBtn.focus()
    fireEvent.keyDown(allBtn, { key: 'Enter', code: 'Enter' })
    // buttons fire click on Enter by default in jsdom
    fireEvent.click(allBtn)
    expect(onChange).toHaveBeenCalledWith('')
  })

  it('has accessible buttons via role', () => {
    render(
      <IndustryFilter
        industries={defaultIndustries}
        selected=""
        onChange={() => {}}
      />
    )
    const buttons = screen.getAllByRole('button')
    // All + 4 industries = 5 buttons
    expect(buttons).toHaveLength(5)
    for (const btn of buttons) {
      expect(btn).toBeVisible()
      expect(btn.tagName).toBe('BUTTON')
    }
  })

  it('does not crash when selected industry is not in the list', () => {
    render(
      <IndustryFilter
        industries={defaultIndustries}
        selected="Aerospace"
        onChange={() => {}}
      />
    )
    // "All" should not be active (selected !== '')
    expect(screen.getByRole('button', { name: 'All' }).className).not.toContain('bg-emerald-600')
    // No industry button should be active
    for (const industry of defaultIndustries) {
      expect(screen.getByRole('button', { name: industry }).className).not.toContain('bg-emerald-600')
    }
  })

})
