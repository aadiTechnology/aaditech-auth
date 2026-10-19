import { ThemeProvider } from '@mui/material'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { UserProfile } from '../../auth/types'
import { AuthContext } from '../../store/auth-context'
import { theme } from '../../theme/theme'
import { AppLayout } from './AppLayout'

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

function installMatchMedia(matches: boolean) {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    configurable: true,
    value: (query: string) => ({
      matches,
      media: query,
      onchange: null,
      addListener: () => undefined,
      removeListener: () => undefined,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      dispatchEvent: () => false,
    }),
  })
}

function renderLayout(user: UserProfile, logout = vi.fn().mockResolvedValue(undefined)) {
  render(
    <ThemeProvider theme={theme}>
      <AuthContext.Provider value={{ status: 'authenticated', user, login: vi.fn(), register: vi.fn(), logout }}>
        <MemoryRouter initialEntries={['/app']}>
          <Routes>
            <Route path="/login" element={<div>Login screen</div>} />
            <Route path="/app" element={<AppLayout />}>
              <Route index element={<div>Dashboard content</div>} />
              <Route path="students" element={<div>Students content</div>} />
              <Route path="parents" element={<div>Parents content</div>} />
              <Route path="admin/access" element={<div>Access content</div>} />
            </Route>
          </Routes>
        </MemoryRouter>
      </AuthContext.Provider>
    </ThemeProvider>,
  )
  return { logout }
}

describe('AppLayout', () => {
  beforeEach(() => {
    installMatchMedia(true)
  })

  it('shows the dashboard link and disables modules that are not built yet', () => {
    renderLayout(teacher)
    expect(screen.getByRole('navigation', { name: 'Main navigation' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Dashboard' })).toHaveAttribute('href', '/app')
    expect(screen.getByRole('heading', { name: 'Dashboard' })).toBeInTheDocument()
    for (const name of ['Google Meet', 'Attendance', 'Fees', 'Receipts']) {
      expect(screen.getByRole('button', { name: new RegExp(name, 'i') })).toHaveAttribute('aria-disabled', 'true')
    }
    expect(screen.getAllByText('Coming soon')).toHaveLength(4)
    expect(screen.queryByRole('link', { name: 'Batches' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Timetable' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Students' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Parents' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Access management' })).not.toBeInTheDocument()
  })

  it('opens students and parents for a permitted user', async () => {
    const user = userEvent.setup()
    renderLayout({
      ...teacher,
      permissions: ['features.read', 'students.read', 'parents.read', 'batches.read', 'timetable.read'],
    })
    expect(screen.getByRole('link', { name: 'Students' })).toHaveAttribute('href', '/app/students')
    expect(screen.getByRole('link', { name: 'Parents' })).toHaveAttribute('href', '/app/parents')
    expect(screen.getByRole('link', { name: 'Batches' })).toHaveAttribute('href', '/app/batches')
    expect(screen.getByRole('link', { name: 'Timetable' })).toHaveAttribute('href', '/app/timetable')
    await user.click(screen.getByRole('link', { name: 'Students' }))
    expect(screen.getByText('Students content')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Students' })).toBeInTheDocument()
  })

  it('keeps access management available for a permitted user', async () => {
    const user = userEvent.setup()
    renderLayout({ ...teacher, permissions: ['users.read'] })
    await user.click(screen.getByRole('link', { name: 'Access management' }))
    expect(screen.getByText('Access content')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Access management' })).toBeInTheDocument()
  })

  it('logs out through the account menu', async () => {
    const user = userEvent.setup()
    const { logout } = renderLayout(teacher)
    await user.click(screen.getByRole('button', { name: 'Account menu' }))
    expect(screen.getByText('teacher@example.com')).toBeInTheDocument()
    await user.click(screen.getByRole('menuitem', { name: 'Log out' }))
    expect(logout).toHaveBeenCalledOnce()
    expect(await screen.findByText('Login screen')).toBeInTheDocument()
  })

  it('hides the sidebar behind a menu button on a narrow screen', async () => {
    installMatchMedia(false)
    const user = userEvent.setup()
    renderLayout(teacher)
    expect(screen.queryByRole('link', { name: 'Dashboard' })).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Open navigation' }))
    expect(screen.getByRole('link', { name: 'Dashboard' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Close navigation' }))
    await waitFor(() => {
      expect(screen.queryByRole('link', { name: 'Dashboard' })).not.toBeInTheDocument()
    })
  })
})
