import { ThemeProvider } from '@mui/material'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { UserProfile } from '../../auth/types'
import { ApiError } from '../../services/api/errors'
import { AuthContext } from '../../store/auth-context'
import { theme } from '../../theme/theme'
import { getStudent } from '../api'
import { StudentDetailPage } from './StudentDetailPage'

vi.mock('../api', () => ({
  getStudent: vi.fn(),
  archiveStudent: vi.fn(),
  linkParent: vi.fn(),
  unlinkParent: vi.fn(),
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
  permissions: ['students.read'],
}

describe('StudentDetailPage', () => {
  beforeEach(() => {
    vi.mocked(getStudent).mockReset()
  })

  it('explains when the student does not exist', async () => {
    vi.mocked(getStudent).mockRejectedValue(new ApiError('Student not found.', 404, 'NOT_FOUND'))
    render(
      <ThemeProvider theme={theme}>
        <AuthContext.Provider
          value={{ status: 'authenticated', user: staff, login: vi.fn(), register: vi.fn(), logout: vi.fn() }}
        >
          <MemoryRouter initialEntries={['/app/students/missing']}>
            <Routes>
              <Route path="/app/students/:studentId" element={<StudentDetailPage />} />
            </Routes>
          </MemoryRouter>
        </AuthContext.Provider>
      </ThemeProvider>,
    )
    expect(await screen.findByText('This student could not be found.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Back to students' })).toHaveAttribute('href', '/app/students')
  })
})
