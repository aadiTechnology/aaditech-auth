import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import type { UserProfile } from '../auth/types'
import { ApiError } from '../services/api/errors'
import { api, ensureCsrf } from '../services/api/client'
import { AuthProvider, useAuth } from './auth-context'

vi.mock('../services/api/client', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
  },
  ensureCsrf: vi.fn(),
  setUnauthorizedHandler: vi.fn(),
}))

const teacher: UserProfile = {
  id: 'teacher-id',
  full_name: 'Meera Kulkarni',
  email: 'teacher@example.com',
  preferred_language: 'en',
  is_active: true,
  email_verified: true,
  roles: ['TEACHER'],
  permissions: ['features.read'],
}

function Probe() {
  const { status, login, logout } = useAuth()
  return (
    <div>
      <p>status:{status}</p>
      <button type="button" onClick={() => void login({ email: 'teacher@example.com', password: 'secret', remember_me: false })}>
        Do login
      </button>
      <button type="button" onClick={() => void logout()}>
        Do logout
      </button>
    </div>
  )
}

describe('AuthProvider logout', () => {
  it('clears the local session when the logout request fails', async () => {
    const user = userEvent.setup()
    vi.mocked(ensureCsrf).mockResolvedValue()
    vi.mocked(api.get).mockRejectedValue(new ApiError('Please sign in again.', 401, 'UNAUTHENTICATED'))
    vi.mocked(api.post).mockImplementation(async (path: string) => {
      if (path === '/api/v1/auth/login') {
        return { data: teacher, message: 'Login successful.' }
      }
      throw new ApiError('The request could not be completed.', 500, 'REQUEST_FAILED')
    })

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    )

    expect(await screen.findByText('status:unauthenticated')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Do login' }))
    expect(await screen.findByText('status:authenticated')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Do logout' }))
    expect(await screen.findByText('status:unauthenticated')).toBeInTheDocument()
  })
})
