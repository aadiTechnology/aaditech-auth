import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '../services/api/errors'
import { api } from '../services/api/client'
import { loadDashboardMetrics } from './metrics'

vi.mock('../services/api/client', () => ({
  api: { get: vi.fn() },
}))

describe('loadDashboardMetrics', () => {
  beforeEach(() => {
    vi.mocked(api.get).mockReset()
  })

  it('uses live student, batch, and class counts and leaves fees unavailable', async () => {
    vi.mocked(api.get).mockImplementation(async (path: string) => {
      if (path.includes('/students/')) {
        return { data: { active_count: 4 }, message: 'Success' }
      }
      if (path.includes('/batches/')) {
        return { data: { active_count: 2 }, message: 'Success' }
      }
      return {
        data: {
          today_count: 1,
          upcoming: [
            {
              id: 'class-1',
              batch_id: 'batch-1',
              batch_name: 'Evening Maths',
              batch_code: 'BAT-000001',
              class_date: '2026-10-19',
              start_time: '17:00:00',
              end_time: '18:00:00',
              topic: 'Algebra',
            },
          ],
        },
        message: 'Success',
      }
    })
    await expect(loadDashboardMetrics()).resolves.toEqual({
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
          class_date: '2026-10-19',
          start_time: '17:00:00',
          end_time: '18:00:00',
          topic: 'Algebra',
        },
      ],
      upcomingStatus: 'ready',
    })
  })

  it('shows zero when the register and timetable are empty', async () => {
    vi.mocked(api.get).mockImplementation(async (path: string) => {
      if (path.includes('/timetable/')) {
        return { data: { today_count: 0, upcoming: [] }, message: 'Success' }
      }
      return { data: { active_count: 0 }, message: 'Success' }
    })
    const result = await loadDashboardMetrics()
    expect(result.metrics[0]).toEqual({ id: 'students', status: 'ready', value: 0, href: '/app/students' })
    expect(result.metrics[2]).toEqual({ id: 'todayClasses', status: 'ready', value: 0, href: '/app/timetable' })
    expect(result.upcomingStatus).toBe('empty')
  })

  it('stays unavailable when the user cannot read a module', async () => {
    vi.mocked(api.get).mockRejectedValue(new ApiError('Forbidden', 403, 'FORBIDDEN'))
    const result = await loadDashboardMetrics()
    expect(result.metrics.map((metric) => metric.status)).toEqual([
      'unavailable',
      'unavailable',
      'unavailable',
      'unavailable',
    ])
    expect(result.upcomingStatus).toBe('unavailable')
    expect(result.metrics.every((metric) => metric.value === null)).toBe(true)
  })

  it('marks a failed count without inventing a number', async () => {
    vi.mocked(api.get).mockImplementation(async (path: string) => {
      if (path.includes('/students/')) {
        throw new ApiError('Failed', 500, 'INTERNAL_ERROR')
      }
      if (path.includes('/batches/')) {
        return { data: { active_count: 3 }, message: 'Success' }
      }
      return { data: { today_count: 0, upcoming: [] }, message: 'Success' }
    })
    const result = await loadDashboardMetrics()
    expect(result.metrics[0]).toEqual({ id: 'students', status: 'error', value: null, href: '/app/students' })
    expect(result.metrics[1]).toEqual({ id: 'batches', status: 'ready', value: 3, href: '/app/batches' })
  })
})
