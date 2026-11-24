import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { I18nProvider, translate } from '../i18n'
import { StatusBadge } from '../components/ui'
import { BarList } from '../components/charts'
import { JourneyPath } from '../pages/me/Beneficiary'

vi.mock('../api/client', async (orig) => {
  const real = await orig()
  return { ...real, api: { get: vi.fn(), post: vi.fn(), patch: vi.fn() }, refreshSession: vi.fn(() => Promise.reject(new Error('no session'))) }
})
import { api } from '../api/client'
import { AuthProvider } from '../auth/AuthContext'
import App from '../App'

const wrap = (ui, path = '/') => render(<MemoryRouter initialEntries={[path]}><I18nProvider>{ui}</I18nProvider></MemoryRouter>)

beforeEach(() => { vi.clearAllMocks(); localStorage.clear() })

describe('i18n', () => {
  it('falls back to English for keys missing in a draft language', () => {
    expect(translate('teo', 'login.title')).toBe('Sign in')
    expect(translate('sw', 'login.title')).toBe('Ingia')
    expect(translate('en', 'ben.inDays', { n: 3 })).toBe('In 3 days')
  })
})

describe('status display', () => {
  it('shows a text label, not colour alone', () => {
    wrap(<StatusBadge status="SENT" group="referralStatus" />)
    expect(screen.getByText('Sent — awaiting acknowledgement')).toBeInTheDocument()
  })

  it('suppresses small cells in charts instead of showing numbers', () => {
    wrap(<BarList minCell={5} rows={[{ key: 'a', label: 'Alpha', value: 12, suppressed: false }, { key: 'b', label: 'Beta', value: null, suppressed: true }]} />)
    expect(screen.getByText('12')).toBeInTheDocument()
    expect(screen.getByText('fewer than 5')).toBeInTheDocument()
  })

  it('marks the current journey step for screen readers', () => {
    wrap(<JourneyPath current="COURT" />)
    const current = screen.getByText('Court').closest('li')
    expect(current).toHaveAttribute('aria-current', 'step')
  })
})

describe('authentication journeys', () => {
  it('shows the login page and a validation message', async () => {
    wrap(<AuthProvider><App /></AuthProvider>, '/app')
    expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))
    expect(await screen.findAllByText('This field is required.')).toHaveLength(2)
  })

  it('sends a caregiver to the beneficiary portal, not the institutional dashboard', async () => {
    api.post.mockResolvedValueOnce({ data: { access: 'x', user: { id: '1', role: 'CAREGIVER', full_name: 'Demo Caregiver', preferred_language: 'en', permissions: { beneficiary_portal: true } } } })
    api.get.mockImplementation((url) => Promise.resolve({ data: url === '/beneficiary/cases/' ? [] : { unread: 0 } }))
    wrap(<AuthProvider><App /></AuthProvider>, '/login')
    await userEvent.type(await screen.findByLabelText('Username'), 'caregiver.demo')
    await userEvent.type(screen.getByLabelText('Password'), 'pw')
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))
    expect(await screen.findByText('Nothing to show yet')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Quick exit/ })).toBeInTheDocument()
    expect(screen.queryByText('Cases')).not.toBeInTheDocument()
  })

  it('shows a generic error for wrong credentials', async () => {
    api.post.mockRejectedValueOnce({ response: { status: 401, data: { error: { message: 'Invalid username or password.' } } } })
    wrap(<AuthProvider><App /></AuthProvider>, '/login')
    await userEvent.type(await screen.findByLabelText('Username'), 'x')
    await userEvent.type(screen.getByLabelText('Password'), 'y')
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))
    await waitFor(() => expect(screen.getByText('Invalid username or password.')).toBeInTheDocument())
  })
})
