import { isIsoDate } from '../roster/format'
import type { ClassFormValues } from './types'
import { withSeconds } from './week'

export function validateClassForm(values: ClassFormValues) {
  const errors: Record<string, string> = {}
  if (!values.batch_id) {
    errors.batch_id = 'REQUIRED'
  }
  if (!values.class_date) {
    errors.class_date = 'REQUIRED'
  } else if (!isIsoDate(values.class_date)) {
    errors.class_date = 'INVALID_DATE'
  }
  if (!values.start_time) {
    errors.start_time = 'REQUIRED'
  }
  if (!values.end_time) {
    errors.end_time = 'REQUIRED'
  } else if (values.start_time && values.end_time <= values.start_time) {
    errors.end_time = 'END_BEFORE_START'
  }
  if (values.repeat) {
    if (values.weekdays.length === 0) {
      errors.weekdays = 'REQUIRED'
    }
    if (values.end_date && !isIsoDate(values.end_date)) {
      errors.end_date = 'INVALID_DATE'
    } else if (values.end_date && values.class_date && values.end_date < values.class_date) {
      errors.end_date = 'INVALID_DATE'
    }
  }
  return errors
}

export function classPayload(values: ClassFormValues, version?: number) {
  const body: Record<string, unknown> = {
    batch_id: values.batch_id,
    class_date: values.class_date,
    start_time: withSeconds(values.start_time),
    end_time: withSeconds(values.end_time),
    topic: values.topic.trim() || null,
    notes: values.notes.trim() || null,
  }
  if (version !== undefined) {
    body.version = version
    return body
  }
  return body
}

export function recurringPayload(values: ClassFormValues) {
  return {
    batch_id: values.batch_id,
    start_date: values.class_date,
    end_date: values.end_date || null,
    weekdays: [...values.weekdays].sort((left, right) => left - right),
    start_time: withSeconds(values.start_time),
    end_time: withSeconds(values.end_time),
    topic: values.topic.trim() || null,
    notes: values.notes.trim() || null,
  }
}
