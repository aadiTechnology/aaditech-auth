import { ThemeProvider } from '@mui/material'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AuthContext } from '../../store/auth-context'
import { theme } from '../../theme/theme'
import { api } from '../../services/api/client'
import { AuthLayout } from '../../layouts/AuthLayout/AuthLayout'
import { LoginPage } from './LoginPage'
import { RegisterPage } from './RegisterPage'
import { ForgotPasswordPage } from './ForgotPasswordPage'
import { ResetPasswordPage } from './ResetPasswordPage'

vi.mock('../../services/api/client', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
  },
  ensureCsrf: vi.fn(),
  setUnauthorizedHandler: vi.fn(),
}))

const policy = {
  min_length: 8,
  require_uppercase: true,
  require_lowercase: true,
  require_number: true,
  require_special: true,
  special_pattern: '[^A-Za-z0-9]',
}

function renderPage(ui: ReactNode, path = '/login') {
  const login = vi.fn().mockResolvedValue(undefined)
  const register = vi.fn().mockResolvedValue('created')
  render(
    <ThemeProvider theme={theme}>
      <AuthContext.Provider
        value={{ status: 'unauthenticated', user: null, login, register, logout: vi.fn() }}
      >
        <MemoryRouter initialEntries={[path]}>{ui}</MemoryRouter>
      </AuthContext.Provider>
    </ThemeProvider>,
  )
  return { login, register }
}

describe('authentication forms', () => {
  beforeEach(() => {
    vi.mocked(api.get).mockResolvedValue({ data: policy, message: 'Success' })
    vi.mocked(api.post).mockReset()
  })

  it('submits the login form', async () => {
    const user = userEvent.setup()
    const { login } = renderPage(<LoginPage />)
    await user.type(screen.getByRole('textbox', { name: /email/i }), 'student@example.com')
    await user.type(screen.getByLabelText(/^password/i), 'ValidPass1!')
    await user.click(screen.getByRole('button', { name: /^sign in$/i }))
    expect(login).toHaveBeenCalledWith({
      email: 'student@example.com',
      password: 'ValidPass1!',
      remember_me: false,
    })
  })

  it('shows a login validation error', async () => {
    const user = userEvent.setup()
    renderPage(<LoginPage />)
    await user.click(screen.getByRole('button', { name: /^sign in$/i }))
    expect(screen.getAllByText('This field is required.').length).toBeGreaterThan(0)
  })

  it('blocks registration when passwords do not match', async () => {
    const user = userEvent.setup()
    const { register } = renderPage(<RegisterPage />)
    await screen.findByRole('button', { name: 'Create account' })
    await user.type(screen.getByRole('textbox', { name: /full name/i }), 'Student User')
    await user.type(screen.getByRole('textbox', { name: /email/i }), 'student@example.com')
    await user.type(screen.getByLabelText(/^password/i), 'ValidPass1!')
    await user.type(screen.getByLabelText(/confirm password/i), 'OtherPass1!')
    await user.click(screen.getByRole('button', { name: /create account/i }))
    expect(screen.getByText('Passwords do not match.')).toBeInTheDocument()
    expect(register).not.toHaveBeenCalled()
  })

  it('shows a generic forgot-password confirmation', async () => {
    const user = userEvent.setup()
    vi.mocked(api.post).mockResolvedValue({ data: {}, message: 'sent' })
    renderPage(<ForgotPasswordPage />)
    await user.type(screen.getByRole('textbox', { name: /email/i }), 'student@example.com')
    await user.click(screen.getByRole('button', { name: /send reset link/i }))
    expect(
      await screen.findByText('If an account exists for this email, password reset instructions have been sent.'),
    ).toBeInTheDocument()
  })

  it('requires a matching confirmation on reset', async () => {
    const user = userEvent.setup()
    renderPage(<ResetPasswordPage />, '/reset-password?token=example-token')
    await screen.findByRole('button', { name: /choose a new password/i })
    await user.type(screen.getByLabelText(/new password/i), 'ValidPass1!')
    await user.type(screen.getByLabelText(/confirm password/i), 'OtherPass1!')
    await user.click(screen.getByRole('button', { name: /choose a new password/i }))
    expect(screen.getByText('Passwords do not match.')).toBeInTheDocument()
    expect(api.post).not.toHaveBeenCalled()
  })

  it('switches the login screen to Marathi', async () => {
    const user = userEvent.setup()
    render(
      <ThemeProvider theme={theme}>
        <AuthContext.Provider
          value={{ status: 'unauthenticated', user: null, login: vi.fn(), register: vi.fn(), logout: vi.fn() }}
        >
          <MemoryRouter initialEntries={['/login']}>
            <Routes>
              <Route element={<AuthLayout />}>
                <Route path="/login" element={<LoginPage />} />
              </Route>
            </Routes>
          </MemoryRouter>
        </AuthContext.Provider>
      </ThemeProvider>,
    )
    await user.selectOptions(screen.getByLabelText(/language/i), 'mr')
    expect(await screen.findByRole('button', { name: 'प्रवेश करा' })).toBeInTheDocument()
  })
})
