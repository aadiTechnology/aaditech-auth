import { ThemeProvider } from '@mui/material'
import { render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { UserProfile } from '../../auth/types'
import { AuthContext } from '../../store/auth-context'
import { theme } from '../../theme/theme'
import { listBatches } from '../../batches/api'
import { listUpcomingMeetings } from '../api'
import { MeetPage } from './MeetPage'

vi.mock('../api', () => ({
  listUpcomingMeetings: vi.fn(),
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
  permissions: ['meet.read', 'meet.update', 'batches.read'],
}

function renderPage() {
  return render(
    <ThemeProvider theme={theme}>
      <AuthContext.Provider
        value={{ status: 'authenticated', user: staff, login: vi.fn(), register: vi.fn(), logout: vi.fn() }}
      >
        <MemoryRouter>
          <MeetPage />
        </MemoryRouter>
      </AuthContext.Provider>
    </ThemeProvider>,
  )
}

describe('MeetPage', () => {
  beforeEach(() => {
    vi.mocked(listBatches).mockReset()
    vi.mocked(listUpcomingMeetings).mockReset()
    vi.mocked(listBatches).mockResolvedValue({ data: { items: [], total: 0, limit: 100, offset: 0 }, message: 'Success' })
  })

  it('shows a missing link and opens only a valid Meet URL', async () => {
    vi.mocked(listUpcomingMeetings).mockResolvedValue({
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
            status: 'scheduled',
            meet_url: null,
            meet_status: 'missing',
          },
          {
            id: 'class-2',
            batch_id: 'batch-2',
            batch_name: 'Science',
            batch_code: 'BAT-000002',
            class_date: '2026-10-21',
            start_time: '18:00:00',
            end_time: '19:00:00',
            topic: null,
            status: 'scheduled',
            meet_url: 'https://meet.google.com/abc-defg-hij',
            meet_status: 'added',
          },
          {
            id: 'class-3',
            batch_id: 'batch-3',
            batch_name: 'Unsafe',
            batch_code: 'BAT-000003',
            class_date: '2026-10-22',
            start_time: '18:00:00',
            end_time: '19:00:00',
            topic: null,
            status: 'scheduled',
            meet_url: 'https://evil.example/meet',
            meet_status: 'added',
          },
        ],
        total: 3,
      },
      message: 'Success',
    })
    renderPage()
    const missing = await screen.findByRole('region', { name: 'Evening Maths' })
    expect(missing).toHaveTextContent('Link missing')
    expect(missing).toHaveTextContent('No meeting link has been added for this class yet.')
    expect(within(missing).queryByRole('link', { name: 'Join meeting' })).not.toBeInTheDocument()

    const ready = screen.getByRole('region', { name: 'Science' })
    const join = within(ready).getByRole('link', { name: 'Join meeting' })
    expect(join).toHaveAttribute('href', 'https://meet.google.com/abc-defg-hij')
    expect(join).toHaveAttribute('target', '_blank')
    expect(join).toHaveAttribute('rel', 'noopener noreferrer')

    expect(within(screen.getByRole('region', { name: 'Unsafe' })).queryByRole('link')).not.toBeInTheDocument()
  })
})
