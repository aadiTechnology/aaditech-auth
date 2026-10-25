import { ThemeProvider } from '@mui/material'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { UserProfile } from '../../auth/types'
import { AuthContext } from '../../store/auth-context'
import { theme } from '../../theme/theme'
import { loadDashboardMetrics } from '../metrics'
import { DashboardPage } from './DashboardPage'

vi.mock('../metrics', () => ({
  loadDashboardMetrics: vi.fn(),
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

function renderDashboard() {
  return render(
    <ThemeProvider theme={theme}>
      <AuthContext.Provider
        value={{ status: 'authenticated', user: teacher, login: vi.fn(), register: vi.fn(), logout: vi.fn() }}
      >
        <MemoryRouter>
          <DashboardPage />
        </MemoryRouter>
      </AuthContext.Provider>
    </ThemeProvider>,
  )
}

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.mocked(loadDashboardMetrics).mockReset()
  })

  it('shows unavailable placeholders and does not invent counts', async () => {
    vi.mocked(loadDashboardMetrics).mockResolvedValue({
      metrics: [
        { id: 'students', status: 'unavailable', value: null },
        { id: 'batches', status: 'unavailable', value: null },
        { id: 'todayClasses', status: 'unavailable', value: null },
        { id: 'pendingFees', status: 'unavailable', value: null },
      ],
      upcoming: [],
      upcomingStatus: 'unavailable',
      todayClasses: [],
      todayStatus: 'unavailable',
      attendanceToday: [],
      attendanceTodayStatus: 'unavailable',
    })
    renderDashboard()
    expect(screen.getByText('Loading summary')).toBeInTheDocument()
    expect(await screen.findAllByText('Not available yet')).toHaveLength(4)
    expect(screen.getByRole('region', { name: 'Total Students' })).toBeInTheDocument()
    expect(screen.getByRole('region', { name: 'Total Batches' })).toBeInTheDocument()
    expect(screen.getByRole('region', { name: "Today's Classes" })).toBeInTheDocument()
    expect(screen.getByRole('region', { name: 'Pending Fees' })).toBeInTheDocument()
    expect(screen.getByText('Signed in as Meera Kulkarni')).toBeInTheDocument()
    expect(screen.getByText('Upcoming classes are not available yet.')).toBeInTheDocument()
    expect(screen.queryByText('0')).not.toBeInTheDocument()
  })

  it('links live counts and upcoming classes', async () => {
    vi.mocked(loadDashboardMetrics).mockResolvedValue({
      metrics: [
        { id: 'students', status: 'ready', value: 4, href: '/app/students' },
        { id: 'batches', status: 'ready', value: 2, href: '/app/batches' },
        { id: 'todayClasses', status: 'ready', value: 1, href: '/app/timetable' },
        { id: 'pendingFees', status: 'unavailable', value: null },
      ],
      upcoming: [
        {
          id: 'class-1',
          batch_id: 'batch-1',
          batch_name: 'Evening Maths',
          batch_code: 'BAT-000001',
          class_date: '2026-10-20',
          start_time: '17:00:00',
          end_time: '18:00:00',
          topic: 'Algebra',
        },
      ],
      upcomingStatus: 'ready',
      todayClasses: [
        {
          id: 'class-1',
          batch_id: 'batch-1',
          batch_name: 'Evening Maths',
          batch_code: 'BAT-000001',
          class_date: '2026-10-20',
          start_time: '17:00:00',
          end_time: '18:00:00',
          topic: 'Algebra',
          meet_url: 'https://meet.google.com/abc-defg-hij',
          meet_status: 'added',
        },
      ],
      todayStatus: 'ready',
      attendanceToday: [
        {
          id: 'class-1',
          batch_id: 'batch-1',
          batch_name: 'Evening Maths',
          class_date: '2026-10-20',
          start_time: '17:00:00',
          end_time: '18:00:00',
          topic: 'Algebra',
          completion: 'not_recorded',
          enrolled_count: 2,
          recorded_count: 0,
        },
      ],
      attendanceTodayStatus: 'ready',
    })
    renderDashboard()
    expect(await screen.findByRole('link', { name: /Total Batches/ })).toHaveAttribute('href', '/app/batches')
    expect(screen.getByRole('link', { name: /Today's Classes/ })).toHaveAttribute('href', '/app/timetable')
    expect(screen.getAllByRole('link', { name: /Evening Maths/ }).length).toBeGreaterThan(0)
    expect(screen.getByRole('link', { name: 'Join meeting' })).toHaveAttribute(
      'href',
      'https://meet.google.com/abc-defg-hij',
    )
    expect(screen.getByRole('link', { name: 'Join meeting' })).toHaveAttribute('target', '_blank')
    expect(screen.getByRole('link', { name: 'Join meeting' })).toHaveAttribute('rel', 'noopener noreferrer')
    expect(screen.getByRole('link', { name: /Not recorded/ })).toHaveAttribute(
      'href',
      '/app/attendance?batch=batch-1&class=class-1',
    )
  })

  it('shows an error when the summary cannot be loaded', async () => {
    vi.mocked(loadDashboardMetrics).mockRejectedValue(new Error('offline'))
    renderDashboard()
    expect(await screen.findByRole('alert')).toHaveTextContent('This summary could not be loaded.')
    expect(screen.queryByText('Not available yet')).not.toBeInTheDocument()
  })

  it('shows an empty state when there are no summary items', async () => {
    vi.mocked(loadDashboardMetrics).mockResolvedValue({ metrics: [], upcoming: [], upcomingStatus: 'empty', todayClasses: [], todayStatus: 'empty', attendanceToday: [], attendanceTodayStatus: 'empty' })
    renderDashboard()
    expect(await screen.findByText('No summary items are available.')).toBeInTheDocument()
  })
})
