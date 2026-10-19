import { ThemeProvider } from '@mui/material'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { UserProfile } from '../../auth/types'
import { AuthContext } from '../../store/auth-context'
import { theme } from '../../theme/theme'
import { createParent } from '../api'
import { ParentFormPage } from './ParentFormPage'

vi.mock('../api', () => ({
  createParent: vi.fn(),
  updateParent: vi.fn(),
  getParent: vi.fn(),
}))

const staff: UserProfile = {
  id: 'staff-id',
  full_name: 'Meera Kulkarni',
  email: 'admin@example.com',
  preferred_language: 'en',
  is_active: true,
  email_verified: true,
  roles: ['ADMIN'],
  permissions: ['parents.create', 'parents.update'],
}

function renderForm() {
  return render(
    <ThemeProvider theme={theme}>
      <AuthContext.Provider
        value={{ status: 'authenticated', user: staff, login: vi.fn(), register: vi.fn(), logout: vi.fn() }}
      >
        <MemoryRouter>
          <ParentFormPage />
        </MemoryRouter>
      </AuthContext.Provider>
    </ThemeProvider>,
  )
}

describe('ParentFormPage', () => {
  beforeEach(() => {
    vi.mocked(createParent).mockReset()
  })

  it('rejects an invalid phone number', async () => {
    const user = userEvent.setup()
    renderForm()
    await user.type(screen.getByRole('textbox', { name: /full name/i }), 'Lata Rao')
    await user.type(screen.getByRole('textbox', { name: /^phone/i }), '12345')
    await user.click(screen.getByRole('button', { name: 'Save parent' }))
    expect(screen.getByRole('textbox', { name: /^phone/i })).toHaveAccessibleDescription('Enter a valid 10-digit mobile number.')
    expect(createParent).not.toHaveBeenCalled()
  })

  it('saves a parent when the phone is valid', async () => {
    vi.mocked(createParent).mockResolvedValue({
      data: {
        id: 'parent-1',
        full_name: 'Lata Rao',
        phone: '+919876543210',
        email: null,
        address: null,
        notes: null,
        status: 'active',
        version: 1,
        archived_at: null,
        students: [],
      },
      message: 'Parent created.',
    })
    const user = userEvent.setup()
    renderForm()
    await user.type(screen.getByRole('textbox', { name: /full name/i }), 'Lata Rao')
    await user.type(screen.getByRole('textbox', { name: /^phone/i }), '9876543210')
    await user.click(screen.getByRole('button', { name: 'Save parent' }))
    expect(createParent).toHaveBeenCalledWith(
      expect.objectContaining({ full_name: 'Lata Rao', phone: '9876543210' }),
    )
  })
})
