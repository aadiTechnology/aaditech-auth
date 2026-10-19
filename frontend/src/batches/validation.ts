import { GRADES } from '../students/types'
import type { BatchFormValues } from './types'

export function validateBatchForm(values: BatchFormValues) {
  const errors: Record<string, string> = {}
  const name = values.name.trim()
  if (!name) {
    errors.name = 'REQUIRED'
  } else if (name.length < 2) {
    errors.name = 'MIN_LENGTH'
  }
  if (values.grade && !GRADES.includes(values.grade as (typeof GRADES)[number])) {
    errors.grade = 'INVALID_GRADE'
  }
  return errors
}

export function batchPayload(values: BatchFormValues, extras?: { version?: number; studentIds?: string[] }) {
  const body: Record<string, unknown> = {
    name: values.name.trim(),
    subject: values.subject.trim() || null,
    grade: values.grade || null,
    description: values.description.trim() || null,
    status: values.status,
  }
  if (extras?.version !== undefined) {
    body.version = extras.version
  }
  if (extras?.studentIds) {
    body.student_ids = extras.studentIds
  }
  return body
}
