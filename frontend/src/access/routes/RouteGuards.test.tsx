import { ThemeProvider } from '@mui/material'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import { AccessDeniedPage } from '../../access/pages/AccessDeniedPage'
import { GuestRoute, PermissionRoute, ProtectedRoute } from '../../access/components/RouteGuards'
import type { UserProfile } from '../../auth/types'
import { LoginPage } from '../../auth/pages/LoginPage'
import { AuthContext } from '../../store/auth-context'
import { theme } from '../../theme/theme'
import { AuthLayout } from '../../layouts/AuthLayout/AuthLayout'
import { api } from '../../services/api/client'

vi.mock('../../services/api/client', () => ({
  api: { get: vi.fn(), post: vi.fn(), patch: vi.fn() },
  ensureCsrf: vi.fn(),
  setUnauthorizedHandler: vi.fn(),
}))

const student: UserProfile = {
  id: 'student-id',
  full_name: 'Student User',
  email: 'student@example.com',
  preferred_language: 'en',
  is_active: true,
  email_verified: false,
  roles: ['STUDENT'],
  permissions: ['features.read'],
}

function renderRoute(path: string, user: UserProfile | null, status: 'authenticated' | 'unauthenticated' = 'authenticated') {
  vi.mocked(api.get).mockResolvedValue({
    data: {
      min_length: 8,
      require_uppercase: true,
      require_lowercase: true,
      require_number: true,
      require_special: true,
      special_pattern: '[^A-Za-z0-9]',
    },
    message: 'Success',
  })
  return render(
    <ThemeProvider theme={theme}>
      <AuthContext.Provider
        value={{ status, user, login: vi.fn(), register: vi.fn(), logout: vi.fn() }}
      >
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/login" element={<GuestRoute><LoginPage /></GuestRoute>} />
            <Route path="/app" element={<ProtectedRoute><div>Private home</div></ProtectedRoute>} />
            <Route
              path="/app/admin/access"
              element={
                <PermissionRoute permission="users.read">
                  <div>Users page</div>
                </PermissionRoute>
              }
            />
            <Route path="/app/access-denied" element={<AccessDeniedPage />} />
          </Routes>
        </MemoryRouter>
      </AuthContext.Provider>
    </ThemeProvider>,
  )
}

describe('route guards', () => {
  it('redirects anonymous visitors away from protected pages', async () => {
    renderRoute('/app', null, 'unauthenticated')
    expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeInTheDocument()
  })

  it('shows protected content to an authenticated user', () => {
    renderRoute('/app', student)
    expect(screen.getByText('Private home')).toBeInTheDocument()
  })

  it('sends users without permission to the access denied page', async () => {
    renderRoute('/app/admin/access', student)
    expect(await screen.findByRole('heading', { name: 'Access denied' })).toBeInTheDocument()
    expect(screen.getByText('You do not have permission to access this page.')).toBeInTheDocument()
  })

  it('allows a permitted user through a permission route', () => {
    renderRoute('/app/admin/access', { ...student, permissions: ['users.read'] })
    expect(screen.getByText('Users page')).toBeInTheDocument()
  })
})

describe('auth layout', () => {
  it('uses a full-width card within the viewport', () => {
    render(
      <ThemeProvider theme={theme}>
        <MemoryRouter initialEntries={['/login']}>
          <Routes>
            <Route element={<AuthLayout />}>
              <Route path="/login" element={<div>Form</div>} />
            </Route>
          </Routes>
        </MemoryRouter>
      </ThemeProvider>,
    )
    expect(screen.getByTestId('auth-card')).toHaveStyle({ width: '100%' })
  })
})
