import { Alert, Button, Stack, TextField, Typography, Link as MuiLink } from '@mui/material'
import { FormEvent, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import { messageForError } from '../validation/errors'
import { isEmail } from '../validation/password'
import { ErrorAlert } from '../../components/common/ErrorAlert'
import { api } from '../../services/api/client'

export function ForgotPasswordPage() {
  const { t } = useTranslation(['auth', 'validation', 'common'])
  const [email, setEmail] = useState('')
  const [error, setError] = useState('')
  const [fieldError, setFieldError] = useState('')
  const [sent, setSent] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    if (!isEmail(email)) {
      setFieldError(t('validation:email'))
      return
    }
    setFieldError('')
    setError('')
    setSubmitting(true)
    try {
      await api.post('/api/v1/auth/forgot-password', { email: email.trim() })
      setSent(true)
    } catch (requestError) {
      setError(messageForError(requestError, t))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Stack component="form" onSubmit={onSubmit} noValidate spacing={2} sx={{ width: '100%' }}>
      <Typography variant="h1">{t('auth:forgotTitle')}</Typography>
      <Typography color="text.secondary">{t('auth:forgotDescription')}</Typography>
      {sent ? <Alert severity="success">{t('auth:resetSent')}</Alert> : null}
      {error ? <ErrorAlert message={error} /> : null}
      <TextField
        id="email"
        name="email"
        type="email"
        label={t('auth:email')}
        autoComplete="email"
        value={email}
        required
        fullWidth
        error={Boolean(fieldError)}
        helperText={fieldError}
        disabled={submitting}
        onChange={(event) => setEmail(event.target.value)}
      />
      <Button type="submit" variant="contained" disabled={submitting}>
        {submitting ? t('auth:submitting') : t('auth:sendResetLink')}
      </Button>
      <MuiLink component={Link} to="/login">
        {t('auth:backToLogin')}
      </MuiLink>
    </Stack>
  )
}
