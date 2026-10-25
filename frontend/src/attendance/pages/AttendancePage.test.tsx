import { ThemeProvider } from '@mui/material'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { UserProfile } from '../../auth/types'
import { AuthContext } from '../../store/auth-context'
import { theme } from '../../theme/theme'
import { listBatches } from '../../batches/api'
import { getRoster, listAttendanceClasses, listHistory, listSummary, saveAttendance } from '../api'
import type { ClassRoster } from '../types'
import { AttendancePage } from './AttendancePage'

vi.mock('../api', () => ({
  listAttendanceClasses: vi.fn(),
  getRoster: vi.fn(),
  saveAttendance: vi.fn(),
  listHistory: vi.fn(),
  listSummary: vi.fn(),
}))

vi.mock('../../batches/api', () => ({
  listBatches: vi.fn(),
}))

const staff: UserProfile = {
  id: 'staff-id',
  full_name: 'Meera Kulkarni',
  email: 'admin@example.com',
  preferred_language: 'en',
  is_active: true,
  email_verified: true,
  roles: ['ADMIN'],
  permissions: ['attendance.read', 'attendance.update', 'batches.read'],
}

const roster: ClassRoster = {
  id: 'class-1',
  batch_id: 'batch-1',
  batch_name: 'Evening Maths',
  batch_code: 'BAT-000001',
  class_date: '2026-10-20',
  start_time: '17:00:00',
  end_time: '18:00:00',
  topic: 'Algebra',
  class_status: 'scheduled',
  completion: 'not_recorded',
  enrolled_count: 2,
  recorded_count: 0,
  students: [
    {
      student_id: 'student-1',
      student_code: 'STU-000001',
      full_name: 'Asha Kulkarni',
      student_status: 'active',
      attendance: null,
    },
    {
      student_id: 'student-2',
      student_code: 'STU-000002',
      full_name: 'Rahul Patil',
      student_status: 'active',
      attendance: null,
    },
  ],
}

function renderPage() {
  return render(
    <ThemeProvider theme={theme}>
      <AuthContext.Provider
        value={{ status: 'authenticated', user: staff, login: vi.fn(), register: vi.fn(), logout: vi.fn() }}
      >
        <MemoryRouter initialEntries={['/app/attendance?batch=batch-1&class=class-1']}>
          <AttendancePage />
        </MemoryRouter>
      </AuthContext.Provider>
    </ThemeProvider>,
  )
}

describe('AttendancePage', () => {
  beforeEach(() => {
    vi.mocked(listBatches).mockReset()
    vi.mocked(listAttendanceClasses).mockReset()
    vi.mocked(getRoster).mockReset()
    vi.mocked(saveAttendance).mockReset()
    vi.mocked(listHistory).mockReset()
    vi.mocked(listSummary).mockReset()
    vi.mocked(listBatches).mockResolvedValue({
      data: {
        items: [
          {
            id: 'batch-1',
            batch_code: 'BAT-000001',
            name: 'Evening Maths',
            subject: 'Maths',
            grade: '8',
            status: 'active',
            student_count: 2,
            next_class: null,
          },
        ],
        total: 1,
        limit: 100,
        offset: 0,
      },
      message: 'Success',
    })
    vi.mocked(listAttendanceClasses).mockResolvedValue({
      data: {
        items: [
          {
            id: 'class-1',
            batch_id: 'batch-1',
            batch_name: 'Evening Maths',
            batch_code: 'BAT-000001',
            class_date: '2026-10-20',
            start_time: '17:00:00',
            end_time: '18:00:00',
            topic: 'Algebra',
            class_status: 'scheduled',
            completion: 'not_recorded',
            enrolled_count: 2,
            recorded_count: 0,
          },
        ],
        total: 1,
      },
      message: 'Success',
    })
    vi.mocked(getRoster).mockResolvedValue({ data: roster, message: 'Success' })
    vi.mocked(listHistory).mockResolvedValue({ data: { items: [], total: 0 }, message: 'Success' })
    vi.mocked(listSummary).mockResolvedValue({ data: { items: [] }, message: 'Success' })
    vi.mocked(saveAttendance).mockResolvedValue({
      data: {
        ...roster,
        completion: 'partial',
        recorded_count: 1,
        students: roster.students.map((student) =>
          student.student_id === 'student-1'
            ? {
                ...student,
                attendance: {
                  id: 'mark-1',
                  status: 'present',
                  notes: null,
                  version: 1,
                  updated_at: '2026-10-19T12:00:00Z',
                },
              }
            : student,
        ),
      },
      message: 'Attendance saved.',
    })
  })

  it('saves only the student who was marked and leaves the other unrecorded', async () => {
    const user = userEvent.setup()
    renderPage()
    const asha = await screen.findByRole('region', { name: 'Asha Kulkarni' })
    const rahul = screen.getByRole('region', { name: 'Rahul Patil' })
    expect(asha).toHaveTextContent('Not recorded')
    expect(rahul).toHaveTextContent('Not recorded')
    expect(within(rahul).getByRole('button', { name: 'Absent' })).toHaveAttribute('aria-pressed', 'false')
    expect(screen.getByText('No attendance has been recorded for this range.')).toBeInTheDocument()

    await user.click(within(asha).getByRole('button', { name: 'Present' }))
    await user.click(screen.getByRole('button', { name: 'Save attendance' }))

    expect(saveAttendance).toHaveBeenCalledWith('class-1', [
      { student_id: 'student-1', status: 'present', notes: null, version: null },
    ])
    expect(within(rahul).getByRole('button', { name: 'Absent' })).toHaveAttribute('aria-pressed', 'false')
  })
})
