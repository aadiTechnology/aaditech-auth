import { ThemeProvider } from '@mui/material'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { UserProfile } from '../../auth/types'
import { AuthContext } from '../../store/auth-context'
import { theme } from '../../theme/theme'
import { listBatches } from '../api'
import { BatchListPage } from './BatchListPage'

vi.mock('../api', () => ({
  listBatches: vi.fn(),
  archiveBatch: vi.fn(),
}))

const staff: UserProfile = {
  id: 'staff-id',
  full_name: 'Meera Kulkarni',
  email: 'admin@example.com',
  preferred_language: 'en',
  is_active: true,
  email_verified: true,
  roles: ['ADMIN'],
  permissions: ['batches.read', 'batches.create', 'batches.update', 'batches.archive'],
}

function renderPage() {
  return render(
    <ThemeProvider theme={theme}>
      <AuthContext.Provider
        value={{ status: 'authenticated', user: staff, login: vi.fn(), register: vi.fn(), logout: vi.fn() }}
      >
        <MemoryRouter>
          <BatchListPage />
        </MemoryRouter>
      </AuthContext.Provider>
    </ThemeProvider>,
  )
}

describe('BatchListPage', () => {
  beforeEach(() => {
    vi.mocked(listBatches).mockReset()
  })

  it('shows a batch with its code, subject, and student count', async () => {
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
            next_class: {
              id: 'class-1',
              class_date: '2026-10-20',
              start_time: '17:00:00',
              end_time: '18:00:00',
            },
          },
        ],
        total: 1,
        limit: 20,
        offset: 0,
      },
      message: 'Success',
    })
    renderPage()
    expect(await screen.findByText('Evening Maths')).toBeInTheDocument()
    expect(screen.getByText('BAT-000001')).toBeInTheDocument()
    expect(screen.getByText('Maths')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
    expect(screen.getByText('20/10/2026 17:00')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Create batch' })).toHaveAttribute('href', '/app/batches/new')
  })

  it('shows an empty state', async () => {
    vi.mocked(listBatches).mockResolvedValue({
      data: { items: [], total: 0, limit: 20, offset: 0 },
      message: 'Success',
    })
    renderPage()
    expect(await screen.findByText('No batches yet. Create a batch to group students.')).toBeInTheDocument()
  })
})
