import { isEmail } from '../auth/validation/password'
import { isMobileNumber } from '../roster/format'
import type { ParentFormValues } from './types'

export function validateParentForm(values: ParentFormValues) {
  const errors: Record<string, string> = {}
  const name = values.full_name.trim()
  if (!name) {
    errors.full_name = 'REQUIRED'
  } else if (name.length < 2) {
    errors.full_name = 'NAME_TOO_SHORT'
  }
  if (values.phone.trim() && !isMobileNumber(values.phone)) {
    errors.phone = 'INVALID_PHONE'
  }
  if (values.email.trim() && !isEmail(values.email)) {
    errors.email = 'INVALID_EMAIL'
  }
  return errors
}

export function parentPayload(values: ParentFormValues, version?: number) {
  const body: Record<string, unknown> = {
    full_name: values.full_name.trim(),
    phone: values.phone.trim() || null,
    email: values.email.trim() || null,
    address: values.address.trim() || null,
    notes: values.notes.trim() || null,
  }
  if (version !== undefined) {
    body.version = version
    if (values.status === 'active') {
      body.status = 'active'
    }
  }
  return body
}
