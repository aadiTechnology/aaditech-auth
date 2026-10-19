import { isEmail } from '../auth/validation/password'
import { isIsoDate, isMobileNumber } from '../roster/format'
import { GRADES, type StudentFormValues } from './types'

export function validateStudentForm(values: StudentFormValues, mode: 'create' | 'edit') {
  const errors: Record<string, string> = {}
  const name = values.full_name.trim()
  if (!name) {
    errors.full_name = 'REQUIRED'
  } else if (name.length < 2) {
    errors.full_name = 'NAME_TOO_SHORT'
  }
  if (values.date_of_birth && !isIsoDate(values.date_of_birth)) {
    errors.date_of_birth = 'INVALID_DATE'
  }
  if (values.enrollment_date && !isIsoDate(values.enrollment_date)) {
    errors.enrollment_date = 'INVALID_DATE'
  }
  if (values.grade && !GRADES.includes(values.grade as (typeof GRADES)[number])) {
    errors.grade = 'INVALID_GRADE'
  }
  if (mode === 'create' && values.parentMode === 'existing' && !values.parent_id) {
    errors.parent_id = 'REQUIRED'
  }
  if (mode === 'create' && values.parentMode === 'new') {
    const parentName = values.parent_full_name.trim()
    if (!parentName) {
      errors.parent_full_name = 'REQUIRED'
    } else if (parentName.length < 2) {
      errors.parent_full_name = 'NAME_TOO_SHORT'
    }
    if (values.parent_phone.trim() && !isMobileNumber(values.parent_phone)) {
      errors.parent_phone = 'INVALID_PHONE'
    }
    if (values.parent_email.trim() && !isEmail(values.parent_email)) {
      errors.parent_email = 'INVALID_EMAIL'
    }
  }
  return errors
}

export function studentPayload(values: StudentFormValues, version?: number) {
  const body: Record<string, unknown> = {
    full_name: values.full_name.trim(),
    date_of_birth: values.date_of_birth || null,
    school_name: values.school_name.trim() || null,
    grade: values.grade || null,
    address: values.address.trim() || null,
    enrollment_date: values.enrollment_date || null,
    notes: values.notes.trim() || null,
  }
  if (values.status === 'active' || values.status === 'inactive') {
    body.status = values.status
  }
  if (version !== undefined) {
    body.version = version
    return body
  }
  if (values.parentMode === 'existing') {
    body.parent_link = {
      parent_id: values.parent_id,
      relationship: values.relationship || null,
    }
  }
  if (values.parentMode === 'new') {
    body.parent_link = {
      full_name: values.parent_full_name.trim(),
      phone: values.parent_phone.trim() || null,
      email: values.parent_email.trim() || null,
      relationship: values.relationship || null,
    }
  }
  return body
}
