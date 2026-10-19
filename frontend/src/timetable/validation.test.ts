import { describe, expect, it } from 'vitest'

import { emptyClassForm } from './types'
import { validateClassForm } from './validation'

describe('validateClassForm', () => {
  it('rejects an end time that is not later than the start', () => {
    expect(
      validateClassForm({
        ...emptyClassForm,
        batch_id: 'batch-1',
        class_date: '2026-10-20',
        start_time: '11:00',
        end_time: '11:00',
      }),
    ).toMatchObject({ end_time: 'END_BEFORE_START' })
  })

  it('allows a class that would start when another could end', () => {
    expect(
      validateClassForm({
        ...emptyClassForm,
        batch_id: 'batch-1',
        class_date: '2026-10-20',
        start_time: '11:00',
        end_time: '12:00',
      }),
    ).toEqual({})
  })
})
