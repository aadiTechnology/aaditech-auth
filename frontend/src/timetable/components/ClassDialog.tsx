import {
  Button,
  Checkbox,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  MenuItem,
  Stack,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from '@mui/material'
import useMediaQuery from '@mui/material/useMediaQuery'
import { useTheme } from '@mui/material/styles'
import { FormEvent, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { usePermission } from '../../access/hooks/usePermission'
import { fieldMessages, messageForError } from '../../auth/validation/errors'
import { ConfirmDialog } from '../../components/common/ConfirmDialog'
import { ErrorAlert } from '../../components/common/ErrorAlert'
import { formatClock, formatDisplayDate } from '../../roster/format'
import { ApiError } from '../../services/api/errors'
import type { BatchListItem } from '../../batches/types'
import { cancelClass, createClass, createRecurring, getClass, previewRecurring, updateClass } from '../api'
import { emptyClassForm, type ClassFormValues, type PreviewData } from '../types'
import { classPayload, recurringPayload, validateClassForm } from '../validation'

export function ClassDialog({
  open,
  classId,
  batches,
  defaultDate,
  defaultBatchId,
  onClose,
  onSaved,
}: {
  open: boolean
  classId: string | null
  batches: BatchListItem[]
  defaultDate: string
  defaultBatchId: string
  onClose: () => void
  onSaved: (message: string) => void
}) {
  const { t } = useTranslation(['timetable', 'validation', 'common'])
  const { hasPermission } = usePermission()
  const theme = useTheme()
  const fullScreen = useMediaQuery(theme.breakpoints.down('sm'))
  const editing = Boolean(classId)
  const canEdit = hasPermission('timetable.update')
  const canCreate = hasPermission('timetable.create')
  const canCancel = hasPermission('timetable.cancel')
  const writable = editing ? canEdit : canCreate
  const [values, setValues] = useState<ClassFormValues>(emptyClassForm)
  const [version, setVersion] = useState(1)
  const [status, setStatus] = useState('scheduled')
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [formError, setFormError] = useState('')
  const [loading, setLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [preview, setPreview] = useState<PreviewData | null>(null)
  const [previewKey, setPreviewKey] = useState('')
  const [cancelOpen, setCancelOpen] = useState(false)

  const formKey = JSON.stringify({
    batch_id: values.batch_id,
    class_date: values.class_date,
    start_time: values.start_time,
    end_time: values.end_time,
    weekdays: values.weekdays,
    end_date: values.end_date,
    topic: values.topic,
    notes: values.notes,
  })

  useEffect(() => {
    if (!open) {
      return
    }
    setErrors({})
    setFormError('')
    setPreview(null)
    setPreviewKey('')
    setCancelOpen(false)
    if (!classId) {
      const active = batches.find((batch) => batch.id === defaultBatchId && batch.status === 'active')
      const fallback = batches.find((batch) => batch.status === 'active')
      setValues({
        ...emptyClassForm,
        batch_id: active?.id ?? fallback?.id ?? '',
        class_date: defaultDate,
      })
      setStatus('scheduled')
      setVersion(1)
      return
    }
    let cancelled = false
    setLoading(true)
    getClass(classId)
      .then((result) => {
        if (cancelled) {
          return
        }
        const item = result.data
        setVersion(item.version)
        setStatus(item.status)
        setValues({
          ...emptyClassForm,
          batch_id: item.batch_id,
          class_date: item.class_date,
          start_time: item.start_time.slice(0, 5),
          end_time: item.end_time.slice(0, 5),
          topic: item.topic ?? '',
          notes: item.notes ?? '',
        })
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setFormError(messageForError(error, t))
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
  }, [open, classId, batches, defaultBatchId, defaultDate, t])

  function setField<K extends keyof ClassFormValues>(key: K, value: ClassFormValues[K]) {
    setValues((current) => ({ ...current, [key]: value }))
    setPreview(null)
    setPreviewKey('')
  }

  function applyErrors(error: unknown) {
    if (error instanceof ApiError) {
      setErrors(fieldMessages(error, t, null))
    }
    setFormError(messageForError(error, t))
  }

  async function onPreview() {
    const local = validateClassForm({ ...values, repeat: true })
    const translated = translateErrors(local, t)
    setErrors(translated)
    setFormError('')
    if (Object.keys(translated).length > 0) {
      return
    }
    setSubmitting(true)
    try {
      const result = await previewRecurring(recurringPayload({ ...values, repeat: true }))
      setPreview(result.data)
      setPreviewKey(formKey)
      if (result.data.conflict_count > 0) {
        setFormError(t('timetable:previewConflict'))
      }
    } catch (error) {
      applyErrors(error)
    } finally {
      setSubmitting(false)
    }
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    if (submitting || !writable || status === 'cancelled') {
      return
    }
    const local = validateClassForm(values)
    const translated = translateErrors(local, t)
    setErrors(translated)
    setFormError('')
    if (Object.keys(translated).length > 0) {
      return
    }
    if (values.repeat && previewKey !== formKey) {
      setFormError(t('timetable:previewRequired'))
      return
    }
    if (values.repeat && preview && preview.conflict_count > 0) {
      setFormError(t('timetable:previewConflict'))
      return
    }
    setSubmitting(true)
    try {
      if (values.repeat) {
        const created = await createRecurring(recurringPayload(values))
        onSaved(t('timetable:createdMany', { count: created.data.total }))
      } else if (classId) {
        await updateClass(classId, classPayload(values, version))
        onSaved(t('timetable:updated'))
      } else {
        await createClass(classPayload(values))
        onSaved(t('timetable:created'))
      }
      onClose()
    } catch (error) {
      applyErrors(error)
    } finally {
      setSubmitting(false)
    }
  }

  async function confirmCancel() {
    if (!classId) {
      return
    }
    setSubmitting(true)
    try {
      await cancelClass(classId)
      setCancelOpen(false)
      onSaved(t('timetable:cancelled'))
      onClose()
    } catch (error) {
      applyErrors(error)
      setCancelOpen(false)
    } finally {
      setSubmitting(false)
    }
  }

  const choices = batches.filter((batch) => batch.status === 'active' || batch.id === values.batch_id)
  const previewFresh = preview !== null && previewKey === formKey

  return (
    <Dialog open={open} onClose={submitting ? undefined : onClose} fullScreen={fullScreen} fullWidth maxWidth="sm">
      <DialogTitle>{editing ? (writable ? t('timetable:edit') : t('timetable:view')) : t('timetable:add')}</DialogTitle>
      <DialogContent>
        <Stack component="form" id="class-form" spacing={2} onSubmit={onSubmit} sx={{ pt: 1 }}>
          {loading ? <Typography>{t('common:loading')}</Typography> : null}
          {formError ? <ErrorAlert message={formError} /> : null}
          <TextField
            select
            label={t('timetable:batch')}
            value={values.batch_id}
            onChange={(event) => setField('batch_id', event.target.value)}
            disabled={!writable || status === 'cancelled'}
            required
            error={Boolean(errors.batch_id)}
            helperText={errors.batch_id || (choices.length === 0 ? t('timetable:noBatches') : undefined)}
          >
            {choices.map((batch) => (
              <MenuItem key={batch.id} value={batch.id}>
                {batch.name} ({batch.batch_code})
              </MenuItem>
            ))}
          </TextField>
          <TextField
            type="date"
            label={t('timetable:date')}
            value={values.class_date}
            onChange={(event) => setField('class_date', event.target.value)}
            disabled={!writable || status === 'cancelled'}
            required
            error={Boolean(errors.class_date)}
            helperText={errors.class_date}
            slotProps={{ inputLabel: { shrink: true } }}
          />
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5}>
            <TextField
              type="time"
              label={t('timetable:startTime')}
              value={values.start_time}
              onChange={(event) => setField('start_time', event.target.value)}
              disabled={!writable || status === 'cancelled'}
              required
              error={Boolean(errors.start_time)}
              helperText={errors.start_time}
              slotProps={{ inputLabel: { shrink: true } }}
              fullWidth
            />
            <TextField
              type="time"
              label={t('timetable:endTime')}
              value={values.end_time}
              onChange={(event) => setField('end_time', event.target.value)}
              disabled={!writable || status === 'cancelled'}
              required
              error={Boolean(errors.end_time)}
              helperText={errors.end_time}
              slotProps={{ inputLabel: { shrink: true } }}
              fullWidth
            />
          </Stack>
          <TextField
            label={t('timetable:topic')}
            value={values.topic}
            onChange={(event) => setField('topic', event.target.value)}
            disabled={!writable || status === 'cancelled'}
            error={Boolean(errors.topic)}
            helperText={errors.topic}
            slotProps={{ htmlInput: { maxLength: 200 } }}
          />
          <TextField
            label={t('timetable:notes')}
            value={values.notes}
            onChange={(event) => setField('notes', event.target.value)}
            disabled={!writable || status === 'cancelled'}
            multiline
            minRows={2}
            error={Boolean(errors.notes)}
            helperText={errors.notes}
            slotProps={{ htmlInput: { maxLength: 2000 } }}
          />
          {!editing && canCreate ? (
            <Stack spacing={1}>
              <FormControlLabel
                control={<Checkbox checked={values.repeat} onChange={(event) => setField('repeat', event.target.checked)} />}
                label={t('timetable:repeat')}
              />
              {values.repeat ? (
                <Stack spacing={1.5}>
                  <Typography id="weekday-label">{t('timetable:weekdays')}</Typography>
                  <ToggleButtonGroup
                    aria-labelledby="weekday-label"
                    value={values.weekdays}
                    onChange={(_event, next: number[]) => setField('weekdays', next)}
                    sx={{ flexWrap: 'wrap' }}
                  >
                    {[0, 1, 2, 3, 4, 5, 6].map((day) => (
                      <ToggleButton key={day} value={day} aria-label={t(`timetable:daysLong.${day}`)}>
                        {t(`timetable:days.${day}`)}
                      </ToggleButton>
                    ))}
                  </ToggleButtonGroup>
                  {errors.weekdays ? <Typography color="error">{errors.weekdays}</Typography> : null}
                  <TextField
                    type="date"
                    label={t('timetable:endDate')}
                    value={values.end_date}
                    onChange={(event) => setField('end_date', event.target.value)}
                    error={Boolean(errors.end_date)}
                    helperText={errors.end_date || t('timetable:endDateHelp')}
                    slotProps={{ inputLabel: { shrink: true } }}
                  />
                  <Button type="button" variant="outlined" onClick={() => void onPreview()} disabled={submitting} sx={{ alignSelf: 'flex-start' }}>
                    {t('timetable:preview')}
                  </Button>
                  {previewFresh && preview ? (
                    <Stack spacing={0.5}>
                      <Typography fontWeight={700}>{t('timetable:previewTitle')}</Typography>
                      {preview.occurrences.map((item) => (
                        <Typography key={item.class_date} color={item.conflict ? 'error' : 'text.primary'}>
                          {formatDisplayDate(item.class_date)} {formatClock(item.start_time)}–{formatClock(item.end_time)}
                          {item.conflict ? ` — ${t('validation:SCHEDULE_CONFLICT')}` : ''}
                        </Typography>
                      ))}
                    </Stack>
                  ) : null}
                </Stack>
              ) : null}
            </Stack>
          ) : null}
        </Stack>
      </DialogContent>
      <DialogActions sx={{ flexWrap: 'wrap', gap: 1 }}>
        {editing && canCancel && status === 'scheduled' ? (
          <Button color="error" onClick={() => setCancelOpen(true)} disabled={submitting} sx={{ mr: 'auto' }}>
            {t('timetable:cancelClass')}
          </Button>
        ) : null}
        <Button onClick={onClose} disabled={submitting}>
          {t('timetable:close')}
        </Button>
        {writable && status !== 'cancelled' ? (
          <Button type="submit" form="class-form" variant="contained" disabled={submitting || loading}>
            {submitting ? t('timetable:saving') : t('timetable:save')}
          </Button>
        ) : null}
      </DialogActions>
      <ConfirmDialog
        open={cancelOpen}
        title={t('timetable:confirmCancelTitle')}
        description={t('timetable:confirmCancelBody')}
        confirmLabel={t('timetable:cancelClass')}
        busy={submitting}
        onClose={() => setCancelOpen(false)}
        onConfirm={() => void confirmCancel()}
      />
    </Dialog>
  )
}

function translateErrors(local: Record<string, string>, t: (key: string) => string) {
  const translated: Record<string, string> = {}
  for (const [field, code] of Object.entries(local)) {
    translated[field] = t(`validation:${code}`)
  }
  return translated
}
