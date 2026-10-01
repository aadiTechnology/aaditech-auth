import { Button, Stack, Typography, Link as MuiLink } from '@mui/material'
import { FormEvent, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'

import { PasswordField } from '../components/PasswordField'
import { usePasswordPolicy } from '../hooks/usePasswordPolicy'
import { fieldMessages, messageForError } from '../validation/errors'
import { validatePassword } from '../validation/password'
import { ErrorAlert } from '../../components/common/ErrorAlert'
import { ApiError } from '../../services/api/errors'
import { api } from '../../services/api/client'

export function ResetPasswordPage() {
  const { t } = useTranslation(['auth', 'validation', 'common'])
  const [params] = useSearchParams()
  const token = useMemo(() => params.get('token') ?? '', [params])
  const navigate = useNavigate()
  const { policy, error: policyError } = usePasswordPolicy()
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [formError, setFormError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    const next: Record<string, string> = {}
    if (!token) next.token = t('common:errors.INVALID_OR_EXPIRED_TOKEN')
    if (policy) {
      const passwordCode = validatePassword(password, policy)
      if (passwordCode) next.new_password = t(`validation:${passwordCode}`, { count: policy.min_length })
    }
    if (password !== confirmPassword) next.confirm_password = t('validation:passwordMismatch')
    setErrors(next)
    setFormError('')
    if (Object.keys(next).length > 0 || !policy) {
      return
    }
    setSubmitting(true)
    try {
      await api.post('/api/v1/auth/reset-password', {
        token,
        new_password: password,
        confirm_password: confirmPassword,
      })
      navigate('/login', { replace: true, state: { notice: t('auth:resetSuccess') } })
    } catch (error) {
      if (error instanceof ApiError && error.details.length > 0) {
        setErrors(fieldMessages(error, t, policy))
      } else {
        setFormError(messageForError(error, t))
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Stack component="form" onSubmit={onSubmit} noValidate spacing={2} sx={{ width: '100%' }}>
      <Typography variant="h1">{t('auth:resetTitle')}</Typography>
      <Typography color="text.secondary">{t('auth:resetDescription')}</Typography>
      {policyError ? <ErrorAlert message={t('common:unexpectedError')} /> : null}
      {formError ? <ErrorAlert message={formError} /> : null}
      {errors.token ? <ErrorAlert message={errors.token} /> : null}
      <PasswordField
        id="new_password"
        label={t('auth:newPassword')}
        autoComplete="new-password"
        value={password}
        error={errors.new_password}
        disabled={submitting || !policy}
        onChange={setPassword}
      />
      <PasswordField
        id="confirm_password"
        label={t('auth:confirmPassword')}
        autoComplete="new-password"
        value={confirmPassword}
        error={errors.confirm_password}
        disabled={submitting || !policy}
        onChange={setConfirmPassword}
      />
      <Button type="submit" variant="contained" disabled={submitting || !policy}>
        {submitting ? t('auth:submitting') : t('auth:resetTitle')}
      </Button>
      <MuiLink component={Link} to="/login">
        {t('auth:backToLogin')}
      </MuiLink>
    </Stack>
  )
}
