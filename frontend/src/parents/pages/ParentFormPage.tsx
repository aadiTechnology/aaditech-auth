import { Button, MenuItem, Stack, TextField, Typography } from '@mui/material'
import { FormEvent, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { fieldMessages, messageForError } from '../../auth/validation/errors'
import { ErrorAlert } from '../../components/common/ErrorAlert'
import { LoadingScreen } from '../../components/common/LoadingScreen'
import { ApiError } from '../../services/api/errors'
import { createParent, getParent, updateParent } from '../api'
import { emptyParentForm, type ParentFormValues } from '../types'
import { parentPayload, validateParentForm } from '../validation'

export function ParentFormPage() {
  const { parentId } = useParams()
  const mode = parentId ? 'edit' : 'create'
  const { t } = useTranslation(['parents', 'validation', 'common'])
  const navigate = useNavigate()
  const [values, setValues] = useState<ParentFormValues>(emptyParentForm)
  const [version, setVersion] = useState(1)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [formError, setFormError] = useState('')
  const [loading, setLoading] = useState(mode === 'edit')
  const [missing, setMissing] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (!parentId) {
      return
    }
    let cancelled = false
    getParent(parentId)
      .then((result) => {
        if (cancelled) {
          return
        }
        const parent = result.data
        setVersion(parent.version)
        setValues({
          full_name: parent.full_name,
          phone: parent.phone ?? '',
          email: parent.email ?? '',
          address: parent.address ?? '',
          notes: parent.notes ?? '',
          status: parent.status === 'archived' ? 'archived' : 'active',
        })
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          if (error instanceof ApiError && error.status === 404) {
            setMissing(true)
          } else {
            setFormError(messageForError(error, t))
          }
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false)
        }
      })
    return () => {
      cancelled = true
    }
  }, [parentId, t])

  function setField<K extends keyof ParentFormValues>(key: K, value: ParentFormValues[K]) {
    setValues((current) => ({ ...current, [key]: value }))
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    if (submitting) {
      return
    }
    const local = validateParentForm(values)
    const translated: Record<string, string> = {}
    for (const [field, code] of Object.entries(local)) {
      translated[field] = t(`validation:${code}`, { defaultValue: t('validation:INVALID'), count: 2 })
    }
    setErrors(translated)
    setFormError('')
    if (Object.keys(translated).length > 0) {
      return
    }
    setSubmitting(true)
    try {
      if (mode === 'create') {
        const created = await createParent(parentPayload(values))
        navigate(`/app/parents/${created.data.id}`, { replace: true, state: { notice: t('parents:created') } })
      } else if (parentId) {
        await updateParent(parentId, parentPayload(values, version))
        navigate(`/app/parents/${parentId}`, { replace: true, state: { notice: t('parents:updated') } })
      }
    } catch (error) {
      if (error instanceof ApiError && error.code === 'STALE_UPDATE') {
        setFormError(t('parents:stale'))
      } else if (error instanceof ApiError && error.details.length > 0) {
        setErrors(fieldMessages(error, t, null))
        setFormError(messageForError(error, t))
      } else {
        setFormError(messageForError(error, t))
      }
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return <LoadingScreen variant="section" />
  }
  if (missing) {
    return (
      <Stack spacing={2}>
        <Typography>{t('parents:notFound')}</Typography>
        <Button component={Link} to="/app/parents" variant="outlined">
          {t('parents:back')}
        </Button>
      </Stack>
    )
  }

  return (
    <Stack component="form" noValidate onSubmit={onSubmit} spacing={2} sx={{ maxWidth: 720 }}>
      <Typography variant="h2">{mode === 'create' ? t('parents:add') : t('parents:edit')}</Typography>
      <Typography color="text.secondary">{t('parents:formHelp')}</Typography>
      {formError ? <ErrorAlert message={formError} /> : null}
      <TextField
        name="full_name"
        label={t('parents:fullName')}
        value={values.full_name}
        onChange={(event) => setField('full_name', event.target.value)}
        required
        fullWidth
        error={Boolean(errors.full_name)}
        helperText={errors.full_name}
        disabled={submitting}
        autoComplete="name"
      />
      <TextField
        name="phone"
        label={t('parents:phone')}
        value={values.phone}
        onChange={(event) => setField('phone', event.target.value)}
        fullWidth
        error={Boolean(errors.phone)}
        helperText={errors.phone || t('parents:phoneHelp')}
        disabled={submitting}
        autoComplete="tel"
      />
      <TextField
        name="email"
        type="email"
        label={t('parents:email')}
        value={values.email}
        onChange={(event) => setField('email', event.target.value)}
        fullWidth
        error={Boolean(errors.email)}
        helperText={errors.email}
        disabled={submitting}
        autoComplete="email"
      />
      <TextField
        name="address"
        label={t('parents:address')}
        value={values.address}
        onChange={(event) => setField('address', event.target.value)}
        fullWidth
        multiline
        minRows={2}
        disabled={submitting}
      />
      <TextField
        name="notes"
        label={t('parents:notes')}
        value={values.notes}
        onChange={(event) => setField('notes', event.target.value)}
        fullWidth
        multiline
        minRows={2}
        disabled={submitting}
      />
      {mode === 'edit' && values.status === 'archived' ? (
        <TextField
          select
          label={t('parents:status')}
          value={values.status}
          onChange={(event) => setField('status', event.target.value as ParentFormValues['status'])}
          helperText={t('parents:archivedEditHelp')}
          disabled={submitting}
        >
          <MenuItem value="archived">{t('parents:statusArchived')}</MenuItem>
          <MenuItem value="active">{t('parents:statusActive')}</MenuItem>
        </TextField>
      ) : null}
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
        <Button type="submit" variant="contained" disabled={submitting}>
          {submitting ? t('parents:saving') : t('parents:save')}
        </Button>
        <Button component={Link} to={parentId ? `/app/parents/${parentId}` : '/app/parents'} disabled={submitting}>
          {t('common:cancel')}
        </Button>
      </Stack>
    </Stack>
  )
}
