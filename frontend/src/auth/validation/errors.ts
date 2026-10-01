import type { TFunction } from 'i18next'

import type { PasswordPolicy } from '../types'
import { ApiError } from '../../services/api/errors'

export function messageForError(error: unknown, translate: TFunction) {
  if (error instanceof ApiError) {
    return translate(`common:errors.${error.code}`, { defaultValue: error.message })
  }
  return translate('common:unexpectedError')
}

export function fieldMessages(error: ApiError, translate: TFunction, policy: PasswordPolicy | null) {
  const messages: Record<string, string> = {}
  for (const detail of error.details) {
    messages[detail.field] = translate(`validation:${detail.code}`, {
      defaultValue: detail.message,
      count: policy?.min_length ?? 8,
    })
  }
  return messages
}
