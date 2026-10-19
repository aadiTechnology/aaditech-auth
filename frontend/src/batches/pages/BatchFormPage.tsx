import { Button, Chip, MenuItem, Stack, TextField, Typography } from '@mui/material'
import { FormEvent, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { usePermission } from '../../access/hooks/usePermission'
import { fieldMessages, messageForError } from '../../auth/validation/errors'
import { ErrorAlert } from '../../components/common/ErrorAlert'
import { LoadingScreen } from '../../components/common/LoadingScreen'
import { ApiError } from '../../services/api/errors'
import { listStudents } from '../../students/api'
import { GRADES, type StudentListItem } from '../../students/types'
import { createBatch, getBatch, updateBatch } from '../api'
import { emptyBatchForm, type BatchFormValues, type SelectedStudent } from '../types'
import { batchPayload, validateBatchForm } from '../validation'

export function BatchFormPage() {
  const { batchId } = useParams()
  const mode = batchId ? 'edit' : 'create'
  const { t } = useTranslation(['batches', 'validation', 'common'])
  const { hasPermission } = usePermission()
  const navigate = useNavigate()
  const [values, setValues] = useState<BatchFormValues>(emptyBatchForm)
  const [version, setVersion] = useState(1)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [formError, setFormError] = useState('')
  const [loading, setLoading] = useState(mode === 'edit')
  const [missing, setMissing] = useState(false)
  const [locked, setLocked] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [studentQuery, setStudentQuery] = useState('')
  const [studentResults, setStudentResults] = useState<StudentListItem[]>([])
  const [selected, setSelected] = useState<SelectedStudent[]>([])
  const canPickStudents = mode === 'create' && hasPermission('students.read')

  useEffect(() => {
    if (!batchId) {
      return
    }
    let cancelled = false
    setLoading(true)
    getBatch(batchId)
      .then((result) => {
        if (cancelled) {
          return
        }
        const batch = result.data
        setVersion(batch.version)
        setLocked(batch.status === 'archived')
        setValues({
          name: batch.name,
          subject: batch.subject ?? '',
          grade: batch.grade ?? '',
          description: batch.description ?? '',
          status: batch.status === 'inactive' ? 'inactive' : 'active',
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
  }, [batchId, t])

  function setField<K extends keyof BatchFormValues>(key: K, value: BatchFormValues[K]) {
    setValues((current) => ({ ...current, [key]: value }))
  }

  async function searchStudents() {
    setFormError('')
    try {
      const result = await listStudents({ q: studentQuery.trim(), status: 'active', limit: 20 })
      const chosen = new Set(selected.map((student) => student.id))
      setStudentResults(result.data.items.filter((student) => !chosen.has(student.id)))
    } catch (error) {
      setFormError(messageForError(error, t))
    }
  }

  function addStudent(student: StudentListItem) {
    setSelected((current) =>
      current.some((item) => item.id === student.id)
        ? current
        : [...current, { id: student.id, student_code: student.student_code, full_name: student.full_name }],
    )
    setStudentResults((current) => current.filter((item) => item.id !== student.id))
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    if (submitting || locked) {
      return
    }
    const local = validateBatchForm(values)
    const translated: Record<string, string> = {}
    for (const [field, code] of Object.entries(local)) {
      translated[field] = t(`validation:${code}`, { defaultValue: t('validation:INVALID') })
    }
    setErrors(translated)
    setFormError('')
    if (Object.keys(translated).length > 0) {
      return
    }
    setSubmitting(true)
    try {
      if (batchId) {
        await updateBatch(batchId, batchPayload(values, { version }))
        navigate(`/app/batches/${batchId}`, { state: { notice: t('batches:updated') } })
      } else {
        const created = await createBatch(batchPayload(values, { studentIds: selected.map((student) => student.id) }))
        navigate(`/app/batches/${created.data.id}`, { state: { notice: t('batches:created') } })
      }
    } catch (error) {
      if (error instanceof ApiError) {
        setErrors(fieldMessages(error, t, null))
      }
      setFormError(messageForError(error, t))
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
        <Typography>{t('batches:notFound')}</Typography>
        <Button component={Link} to="/app/batches" variant="outlined">
          {t('batches:back')}
        </Button>
      </Stack>
    )
  }

  return (
    <Stack spacing={3} sx={{ maxWidth: 720 }}>
      <Button component={Link} to={batchId ? `/app/batches/${batchId}` : '/app/batches'} variant="outlined" sx={{ alignSelf: 'flex-start' }}>
        {t('batches:back')}
      </Button>
      <Stack spacing={0.5}>
        <Typography variant="h2">{mode === 'edit' ? t('batches:edit') : t('batches:add')}</Typography>
        <Typography color="text.secondary">{locked ? t('batches:archivedEditHelp') : t('batches:formHelp')}</Typography>
      </Stack>
      {formError ? <ErrorAlert message={formError} /> : null}
      <Stack component="form" spacing={2} onSubmit={onSubmit}>
        <TextField
          name="name"
          label={t('batches:name')}
          value={values.name}
          onChange={(event) => setField('name', event.target.value)}
          required
          disabled={locked}
          error={Boolean(errors.name)}
          helperText={errors.name}
          slotProps={{ htmlInput: { maxLength: 200 } }}
        />
        <Typography color="text.secondary">{t('batches:codeHelp')}</Typography>
        <TextField
          name="subject"
          label={t('batches:subject')}
          value={values.subject}
          onChange={(event) => setField('subject', event.target.value)}
          disabled={locked}
          error={Boolean(errors.subject)}
          helperText={errors.subject}
          slotProps={{ htmlInput: { maxLength: 100 } }}
        />
        <TextField
          select
          label={t('batches:grade')}
          value={values.grade}
          onChange={(event) => setField('grade', event.target.value)}
          disabled={locked}
          error={Boolean(errors.grade)}
          helperText={errors.grade}
        >
          <MenuItem value="">{t('batches:allGrades')}</MenuItem>
          {GRADES.map((item) => (
            <MenuItem key={item} value={item}>
              {t('batches:classOption', { grade: item })}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          name="description"
          label={t('batches:descriptionField')}
          value={values.description}
          onChange={(event) => setField('description', event.target.value)}
          disabled={locked}
          multiline
          minRows={3}
          error={Boolean(errors.description)}
          helperText={errors.description}
          slotProps={{ htmlInput: { maxLength: 2000 } }}
        />
        <TextField
          select
          label={t('batches:status')}
          value={values.status}
          onChange={(event) => setField('status', event.target.value as BatchFormValues['status'])}
          disabled={locked}
        >
          <MenuItem value="active">{t('batches:statusActive')}</MenuItem>
          <MenuItem value="inactive">{t('batches:statusInactive')}</MenuItem>
        </TextField>
        {canPickStudents ? (
          <Stack spacing={1.5}>
            <Typography fontWeight={700}>{t('batches:selectedStudents')}</Typography>
            {selected.length === 0 ? <Typography color="text.secondary">{t('batches:noneSelected')}</Typography> : null}
            <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap' }}>
              {selected.map((student) => (
                <Chip
                  key={student.id}
                  label={`${student.full_name} (${student.student_code})`}
                  onDelete={() => setSelected((current) => current.filter((item) => item.id !== student.id))}
                />
              ))}
            </Stack>
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
              <TextField
                label={t('batches:studentSearch')}
                value={studentQuery}
                onChange={(event) => setStudentQuery(event.target.value)}
                size="small"
                fullWidth
              />
              <Button type="button" variant="outlined" onClick={() => void searchStudents()}>
                {t('batches:search')}
              </Button>
            </Stack>
            {studentResults.map((student) => (
              <Button key={student.id} type="button" onClick={() => addStudent(student)} sx={{ justifyContent: 'flex-start' }}>
                {student.full_name} ({student.student_code})
              </Button>
            ))}
          </Stack>
        ) : null}
        {locked ? null : (
          <Button type="submit" variant="contained" disabled={submitting} sx={{ alignSelf: 'flex-start' }}>
            {submitting ? t('batches:saving') : t('batches:save')}
          </Button>
        )}
      </Stack>
    </Stack>
  )
}
