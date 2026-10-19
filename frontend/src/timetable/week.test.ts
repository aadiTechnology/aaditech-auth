import { describe, expect, it } from 'vitest'

import { addDays, coachingToday, startOfWeek, weekDates, withSeconds } from './week'

describe('coaching week', () => {
  it('uses the India calendar date around midnight UTC', () => {
    expect(coachingToday(new Date('2026-10-19T18:30:00Z'))).toBe('2026-10-20')
    expect(coachingToday(new Date('2026-10-19T12:00:00Z'))).toBe('2026-10-19')
  })

  it('starts weeks on Monday and keeps a class on its date', () => {
    expect(startOfWeek('2026-10-19')).toBe('2026-10-19')
    expect(startOfWeek('2026-10-25')).toBe('2026-10-19')
    expect(weekDates('2026-10-19')[6]).toBe('2026-10-25')
    expect(addDays('2026-10-19', 7)).toBe('2026-10-26')
  })

  it('normalizes clock input for the API', () => {
    expect(withSeconds('17:00')).toBe('17:00:00')
    expect(withSeconds('17:00:00')).toBe('17:00:00')
  })
})
