import { ThemeProvider } from '@mui/material'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { UserProfile } from '../../auth/types'
import { AuthContext } from '../../store/auth-context'
import { theme } from '../../theme/theme'
import { listBatches } from '../../batches/api'
import { listClasses } from '../api'
import { TimetablePage } from './TimetablePage'

vi.mock('../api', () => ({
  listClasses: vi.fn(),
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
  permissions: ['timetable.read', 'timetable.create', 'batches.read'],
}

function renderPage() {
  return render(
    <ThemeProvider theme={theme}>
      <AuthContext.Provider
        value={{ status: 'authenticated', user: staff, login: vi.fn(), register: vi.fn(), logout: vi.fn() }}
      >
        <MemoryRouter initialEntries={['/app/timetable?date=2026-10-20']}>
          <TimetablePage />
        </MemoryRouter>
      </AuthContext.Provider>
    </ThemeProvider>,
  )
}

describe('TimetablePage', () => {
  beforeEach(() => {
    vi.mocked(listClasses).mockReset()
    vi.mocked(listBatches).mockReset()
    vi.mocked(listBatches).mockResolvedValue({ data: { items: [], total: 0, limit: 100, offset: 0 }, message: 'Success' })
  })

  it('places a class on its weekday and time', async () => {
    vi.mocked(listClasses).mockResolvedValue({
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
          },
        ],
        total: 1,
      },
      message: 'Success',
    })
    renderPage()
    const day = await screen.findByRole('region', { name: /Tuesday 20\/10\/2026/ })
    expect(day).toHaveTextContent('17:00–18:00')
    expect(day).toHaveTextContent('Evening Maths')
    expect(day).toHaveTextContent('Algebra')
    expect(screen.getByRole('button', { name: 'Add class' })).toBeInTheDocument()
  })

  it('shows an empty week and requests the next week', async () => {
    vi.mocked(listClasses).mockResolvedValue({ data: { items: [], total: 0 }, message: 'Success' })
    const user = userEvent.setup()
    renderPage()
    expect(await screen.findByText('No classes are scheduled this week.')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Next week' }))
    expect(listClasses).toHaveBeenLastCalledWith(
      expect.objectContaining({ from: '2026-10-26', to: '2026-11-01' }),
    )
  })
})
