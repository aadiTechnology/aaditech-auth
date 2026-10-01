import type { PasswordPolicy } from '../types'

const SPECIAL_CHARACTER = /[^A-Za-z0-9]/

export function validatePassword(password: string, policy: PasswordPolicy): string | null {
  if (password.length < policy.min_length) {
    return 'TOO_SHORT'
  }
  if (policy.require_uppercase && !/[A-Z]/.test(password)) {
    return 'MISSING_UPPERCASE'
  }
  if (policy.require_lowercase && !/[a-z]/.test(password)) {
    return 'MISSING_LOWERCASE'
  }
  if (policy.require_number && !/[0-9]/.test(password)) {
    return 'MISSING_NUMBER'
  }
  if (policy.require_special && !SPECIAL_CHARACTER.test(password)) {
    return 'MISSING_SPECIAL'
  }
  return null
}

export function isEmail(value: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim())
}
