import { ThemeProvider } from '@mui/material'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { UserProfile } from '../../auth/types'
import { AuthContext } from '../../store/auth-context'
import { theme } from '../../theme/theme'
import { listStudents } from '../api'
import { StudentListPage } from './StudentListPage'

vi.mock('../api', () => ({
  listStudents: vi.fn(),
  archiveStudent: vi.fn(),
}))

const staff: UserProfile = {
  id: 'staff-id',
  full_name: 'Meera Kulkarni',
  email: 'admin@example.com',
  preferred_language: 'en',
  is_active: true,
  email_verified: true,
  roles: ['ADMIN'],
  permissions: ['students.read', 'students.create', 'students.update', 'students.archive'],
}

const student = {
  id: 'student-1',
  student_code: 'STU-000001',
  full_name: 'Asha Kulkarni',
  grade: '8',
  school_name: 'City High School',
  status: 'active',
  enrollment_date: '2026-06-01',
  parents: [{ id: 'parent-1', full_name: 'Lata Rao', relationship: 'mother' }],
}

function renderPage() {
  return render(
    <ThemeProvider theme={theme}>
      <AuthContext.Provider
        value={{ status: 'authenticated', user: staff, login: vi.fn(), register: vi.fn(), logout: vi.fn() }}
      >
        <MemoryRouter>
          <StudentListPage />
        </MemoryRouter>
      </AuthContext.Provider>
    </ThemeProvider>,
  )
}

describe('StudentListPage', () => {
  beforeEach(() => {
    vi.mocked(listStudents).mockReset()
  })

  it('shows the register without parent phone numbers', async () => {
    vi.mocked(listStudents).mockResolvedValue({
      data: { items: [student], total: 1, limit: 20, offset: 0 },
      message: 'Success',
    })
    renderPage()
    expect(screen.getByRole('status')).toBeInTheDocument()
    expect(await screen.findByText('Asha Kulkarni')).toBeInTheDocument()
    expect(screen.getByText('STU-000001')).toBeInTheDocument()
    expect(screen.getByText('Lata Rao')).toBeInTheDocument()
    expect(screen.getByText('Class 8')).toBeInTheDocument()
    expect(screen.queryByRole('columnheader', { name: /phone/i })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Add student' })).toHaveAttribute('href', '/app/students/new')
  })

  it('shows an empty state', async () => {
    vi.mocked(listStudents).mockResolvedValue({
      data: { items: [], total: 0, limit: 20, offset: 0 },
      message: 'Success',
    })
    renderPage()
    expect(await screen.findByText('No students yet. Add a student to start the class register.')).toBeInTheDocument()
  })

  it('shows an error state', async () => {
    vi.mocked(listStudents).mockRejectedValue(new Error('offline'))
    renderPage()
    expect(await screen.findByRole('alert')).toHaveTextContent('Something went wrong. Please try again.')
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument()
  })

  it('searches by the entered name', async () => {
    vi.mocked(listStudents).mockResolvedValue({
      data: { items: [], total: 0, limit: 20, offset: 0 },
      message: 'Success',
    })
    const user = userEvent.setup()
    renderPage()
    await screen.findByText('No students yet. Add a student to start the class register.')
    await user.type(screen.getByLabelText('Search by name or student ID'), 'Asha')
    await user.click(screen.getByRole('button', { name: 'Search' }))
    expect(listStudents).toHaveBeenCalledWith(expect.objectContaining({ q: 'Asha' }))
  })
})
