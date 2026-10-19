import { ThemeProvider } from '@mui/material'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { UserProfile } from '../../auth/types'
import { ApiError } from '../../services/api/errors'
import { AuthContext } from '../../store/auth-context'
import { theme } from '../../theme/theme'
import { createStudent } from '../api'
import { StudentFormPage } from './StudentFormPage'

vi.mock('../api', () => ({
  createStudent: vi.fn(),
  updateStudent: vi.fn(),
  getStudent: vi.fn(),
}))

vi.mock('../../parents/api', () => ({
  listParents: vi.fn(),
}))

const staff: UserProfile = {
  id: 'staff-id',
  full_name: 'Meera Kulkarni',
  email: 'admin@example.com',
  preferred_language: 'en',
  is_active: true,
  email_verified: true,
  roles: ['ADMIN'],
  permissions: ['students.create', 'parents.read', 'parents.create', 'parents.update'],
}

function renderForm() {
  return render(
    <ThemeProvider theme={theme}>
      <AuthContext.Provider
        value={{ status: 'authenticated', user: staff, login: vi.fn(), register: vi.fn(), logout: vi.fn() }}
      >
        <MemoryRouter initialEntries={['/app/students/new']}>
          <StudentFormPage />
        </MemoryRouter>
      </AuthContext.Provider>
    </ThemeProvider>,
  )
}

describe('StudentFormPage', () => {
  beforeEach(() => {
    vi.mocked(createStudent).mockReset()
  })

  it('requires a name before saving', async () => {
    const user = userEvent.setup()
    renderForm()
    await user.click(screen.getByRole('button', { name: 'Save student' }))
    expect(screen.getByRole('textbox', { name: /full name/i })).toHaveAccessibleDescription('This field is required.')
    expect(createStudent).not.toHaveBeenCalled()
  })

  it('saves a valid student', async () => {
    vi.mocked(createStudent).mockResolvedValue({
      data: {
        id: 'student-1',
        student_code: 'STU-000001',
        full_name: 'Asha Kulkarni',
        date_of_birth: null,
        school_name: null,
        grade: null,
        address: null,
        enrollment_date: null,
        status: 'active',
        notes: null,
        version: 1,
        archived_at: null,
        parents: [],
      },
      message: 'Student created.',
    })
    const user = userEvent.setup()
    renderForm()
    await user.type(screen.getByRole('textbox', { name: /full name/i }), 'Asha Kulkarni')
    await user.click(screen.getByRole('button', { name: 'Save student' }))
    expect(createStudent).toHaveBeenCalledWith(expect.objectContaining({ full_name: 'Asha Kulkarni', status: 'active' }))
  })

  it('shows a server field error', async () => {
    vi.mocked(createStudent).mockRejectedValue(
      new ApiError('Validation failed.', 422, 'VALIDATION_ERROR', [
        { field: 'date_of_birth', code: 'INVALID_DATE', message: 'Enter a valid date of birth.' },
      ]),
    )
    const user = userEvent.setup()
    renderForm()
    await user.type(screen.getByRole('textbox', { name: /full name/i }), 'Asha Kulkarni')
    await user.click(screen.getByRole('button', { name: 'Save student' }))
    expect(await screen.findByText('Enter a valid date.')).toBeInTheDocument()
  })
})
