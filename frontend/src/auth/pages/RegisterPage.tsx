import { Button, MenuItem, Stack, TextField, Typography, Link as MuiLink } from '@mui/material'
import { FormEvent, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'

import { PasswordField } from '../components/PasswordField'
import { usePasswordPolicy } from '../hooks/usePasswordPolicy'
import { fieldMessages, messageForError } from '../validation/errors'
import { isEmail, validatePassword } from '../validation/password'
import { ErrorAlert } from '../../components/common/ErrorAlert'
import i18n, { supportedLanguages, type SupportedLanguage } from '../../i18n'
import { ApiError } from '../../services/api/errors'
import { useAuth } from '../../store/auth-context'

export function RegisterPage() {
  const { t } = useTranslation(['auth', 'validation', 'common'])
  const { register } = useAuth()
  const navigate = useNavigate()
  const { policy, error: policyError } = usePasswordPolicy()
  const initialLanguage = supportedLanguages.includes((i18n.language ?? 'en') as SupportedLanguage)
    ? ((i18n.language.split('-')[0] ?? 'en') as SupportedLanguage)
    : 'en'
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [language, setLanguage] = useState<SupportedLanguage>(initialLanguage)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [formError, setFormError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    const next: Record<string, string> = {}
    if (fullName.trim().length < 2) next.full_name = t('validation:fullNameMin')
    if (!isEmail(email)) next.email = t('validation:email')
    if (policy) {
      const passwordCode = validatePassword(password, policy)
      if (passwordCode) {
        next.password = t(`validation:${passwordCode}`, { count: policy.min_length })
      }
    }
    if (password !== confirmPassword) next.confirm_password = t('validation:passwordMismatch')
    setErrors(next)
    setFormError('')
    if (Object.keys(next).length > 0 || !policy) {
      return
    }
    setSubmitting(true)
    try {
      await register({
        full_name: fullName.trim(),
        email: email.trim(),
        password,
        confirm_password: confirmPassword,
        preferred_language: language,
      })
      void i18n.changeLanguage(language)
      navigate('/login', { replace: true, state: { notice: t('auth:registrationSuccess') } })
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
      <Typography variant="h1">{t('auth:registerTitle')}</Typography>
      <Typography color="text.secondary">{t('auth:registerSubtitle')}</Typography>
      {policyError ? <ErrorAlert message={t('common:unexpectedError')} /> : null}
      {formError ? <ErrorAlert message={formError} /> : null}
      <TextField
        id="full_name"
        name="full_name"
        label={t('auth:fullName')}
        autoComplete="name"
        value={fullName}
        required
        fullWidth
        error={Boolean(errors.full_name)}
        helperText={errors.full_name}
        disabled={submitting}
        onChange={(event) => setFullName(event.target.value)}
      />
      <TextField
        id="email"
        name="email"
        type="email"
        label={t('auth:email')}
        autoComplete="email"
        value={email}
        required
        fullWidth
        error={Boolean(errors.email)}
        helperText={errors.email}
        disabled={submitting}
        onChange={(event) => setEmail(event.target.value)}
      />
      <PasswordField
        id="password"
        label={t('auth:password')}
        autoComplete="new-password"
        value={password}
        error={errors.password}
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
      <TextField
        select
        id="preferred_language"
        label={t('auth:preferredLanguage')}
        value={language}
        fullWidth
        disabled={submitting}
        onChange={(event) => setLanguage(event.target.value as SupportedLanguage)}
      >
        <MenuItem value="en">{t('common:english')}</MenuItem>
        <MenuItem value="mr">{t('common:marathi')}</MenuItem>
        <MenuItem value="hi">{t('common:hindi')}</MenuItem>
      </TextField>
      <Button type="submit" variant="contained" disabled={submitting || !policy}>
        {submitting ? t('auth:submitting') : t('auth:createAccount')}
      </Button>
      <Typography>
        {t('auth:alreadyHaveAccount')}{' '}
        <MuiLink component={Link} to="/login">
          {t('auth:signIn')}
        </MuiLink>
      </Typography>
    </Stack>
  )
}
