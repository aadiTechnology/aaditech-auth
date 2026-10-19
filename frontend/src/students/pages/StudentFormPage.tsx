import {
  Button,
  FormControl,
  FormControlLabel,
  FormLabel,
  MenuItem,
  Radio,
  RadioGroup,
  Stack,
  TextField,
  Typography,
} from '@mui/material'
import { FormEvent, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { usePermission } from '../../access/hooks/usePermission'
import { fieldMessages, messageForError } from '../../auth/validation/errors'
import { ErrorAlert } from '../../components/common/ErrorAlert'
import { LoadingScreen } from '../../components/common/LoadingScreen'
import { ApiError } from '../../services/api/errors'
import { listParents } from '../../parents/api'
import type { ParentListItem } from '../../parents/types'
import { createStudent, getStudent, updateStudent } from '../api'
import { emptyStudentForm, GRADES, type StudentFormValues } from '../types'
import { studentPayload, validateStudentForm } from '../validation'

export function StudentFormPage() {
  const { studentId } = useParams()
  const mode = studentId ? 'edit' : 'create'
  const { t } = useTranslation(['students', 'validation', 'common'])
  const { hasPermission } = usePermission()
  const navigate = useNavigate()
  const [values, setValues] = useState<StudentFormValues>(emptyStudentForm)
  const [version, setVersion] = useState(1)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [formError, setFormError] = useState('')
  const [loading, setLoading] = useState(mode === 'edit')
  const [missing, setMissing] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [parentQuery, setParentQuery] = useState('')
  const [parentResults, setParentResults] = useState<ParentListItem[]>([])
  const [searchingParents, setSearchingParents] = useState(false)
  const canLinkExisting = hasPermission('parents.read') && hasPermission('parents.update')
  const canCreateParent = hasPermission('parents.create')

  useEffect(() => {
    if (!studentId) {
      return
    }
    let cancelled = false
    setLoading(true)
    getStudent(studentId)
      .then((result) => {
        if (cancelled) {
          return
        }
        const student = result.data
        setVersion(student.version)
        setValues({
          ...emptyStudentForm,
          full_name: student.full_name,
          status: student.status === 'inactive' || student.status === 'archived' ? student.status : 'active',
          date_of_birth: student.date_of_birth ?? '',
          school_name: student.school_name ?? '',
          grade: student.grade ?? '',
          address: student.address ?? '',
          enrollment_date: student.enrollment_date ?? '',
          notes: student.notes ?? '',
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
  }, [studentId, t])

  function setField<K extends keyof StudentFormValues>(key: K, value: StudentFormValues[K]) {
    setValues((current) => ({ ...current, [key]: value }))
  }

  async function searchParents() {
    setSearchingParents(true)
    setFormError('')
    try {
      const result = await listParents({ q: parentQuery.trim(), status: 'active', limit: 20 })
      setParentResults(result.data.items)
    } catch (error) {
      setFormError(messageForError(error, t))
    } finally {
      setSearchingParents(false)
    }
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    if (submitting) {
      return
    }
    const local = validateStudentForm(values, mode)
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
        const created = await createStudent(studentPayload(values))
        navigate(`/app/students/${created.data.id}`, { replace: true, state: { notice: t('students:created') } })
      } else if (studentId) {
        await updateStudent(studentId, studentPayload(values, version))
        navigate(`/app/students/${studentId}`, { replace: true, state: { notice: t('students:updated') } })
      }
    } catch (error) {
      if (error instanceof ApiError && error.code === 'STALE_UPDATE') {
        setFormError(t('students:stale'))
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
        <Typography>{t('students:notFound')}</Typography>
        <Button component={Link} to="/app/students" variant="outlined">
          {t('students:back')}
        </Button>
      </Stack>
    )
  }

  return (
    <Stack component="form" noValidate onSubmit={onSubmit} spacing={2} sx={{ maxWidth: 720 }}>
      <Typography variant="h2">{mode === 'create' ? t('students:add') : t('students:edit')}</Typography>
      <Typography color="text.secondary">{t('students:formHelp')}</Typography>
      {formError ? <ErrorAlert message={formError} /> : null}
      <TextField
        name="full_name"
        label={t('students:fullName')}
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
        select
        name="status"
        label={t('students:status')}
        value={values.status}
        onChange={(event) => setField('status', event.target.value as StudentFormValues['status'])}
        fullWidth
        disabled={submitting}
        helperText={values.status === 'archived' ? t('students:archivedEditHelp') : undefined}
      >
        {values.status === 'archived' ? <MenuItem value="archived">{t('students:statusArchived')}</MenuItem> : null}
        <MenuItem value="active">{t('students:statusActive')}</MenuItem>
        <MenuItem value="inactive">{t('students:statusInactive')}</MenuItem>
      </TextField>
      <TextField
        name="date_of_birth"
        label={t('students:dateOfBirth')}
        type="date"
        value={values.date_of_birth}
        onChange={(event) => setField('date_of_birth', event.target.value)}
        fullWidth
        slotProps={{ inputLabel: { shrink: true } }}
        error={Boolean(errors.date_of_birth)}
        helperText={errors.date_of_birth}
        disabled={submitting}
      />
      <TextField
        select
        name="grade"
        label={t('students:grade')}
        value={values.grade}
        onChange={(event) => setField('grade', event.target.value)}
        fullWidth
        disabled={submitting}
        error={Boolean(errors.grade)}
        helperText={errors.grade}
      >
        <MenuItem value="">{t('students:notProvided')}</MenuItem>
        {GRADES.map((grade) => (
          <MenuItem key={grade} value={grade}>
            {t('students:classOption', { grade })}
          </MenuItem>
        ))}
      </TextField>
      <TextField
        name="school_name"
        label={t('students:school')}
        value={values.school_name}
        onChange={(event) => setField('school_name', event.target.value)}
        fullWidth
        disabled={submitting}
      />
      <TextField
        name="address"
        label={t('students:address')}
        value={values.address}
        onChange={(event) => setField('address', event.target.value)}
        fullWidth
        multiline
        minRows={2}
        disabled={submitting}
      />
      <TextField
        name="enrollment_date"
        label={t('students:enrollment')}
        type="date"
        value={values.enrollment_date}
        onChange={(event) => setField('enrollment_date', event.target.value)}
        fullWidth
        slotProps={{ inputLabel: { shrink: true } }}
        error={Boolean(errors.enrollment_date)}
        helperText={errors.enrollment_date}
        disabled={submitting}
      />
      <TextField
        name="notes"
        label={t('students:notes')}
        value={values.notes}
        onChange={(event) => setField('notes', event.target.value)}
        fullWidth
        multiline
        minRows={2}
        disabled={submitting}
      />
      {mode === 'create' && (canLinkExisting || canCreateParent) ? (
        <FormControl>
          <FormLabel id="parent-mode">{t('students:parentSection')}</FormLabel>
          <Typography color="text.secondary" sx={{ mb: 1 }}>
            {t('students:parentOptional')}
          </Typography>
          <RadioGroup
            aria-labelledby="parent-mode"
            value={values.parentMode}
            onChange={(event) => setField('parentMode', event.target.value as StudentFormValues['parentMode'])}
          >
            <FormControlLabel value="none" control={<Radio />} label={t('students:parentModeNone')} disabled={submitting} />
            {canLinkExisting ? (
              <FormControlLabel
                value="existing"
                control={<Radio />}
                label={t('students:parentModeExisting')}
                disabled={submitting}
              />
            ) : null}
            {canCreateParent ? (
              <FormControlLabel value="new" control={<Radio />} label={t('students:parentModeNew')} disabled={submitting} />
            ) : null}
          </RadioGroup>
        </FormControl>
      ) : null}
      {mode === 'create' && values.parentMode === 'existing' ? (
        <Stack spacing={1.5}>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
            <TextField
              label={t('students:parentSearch')}
              value={parentQuery}
              onChange={(event) => setParentQuery(event.target.value)}
              fullWidth
              size="small"
              disabled={submitting}
            />
            <Button type="button" variant="outlined" onClick={() => void searchParents()} disabled={searchingParents || submitting}>
              {t('students:search')}
            </Button>
          </Stack>
          {parentResults.length === 0 ? <Typography>{t('students:noParentMatches')}</Typography> : null}
          <RadioGroup
            aria-label={t('students:chooseParent')}
            value={values.parent_id}
            onChange={(event) => setField('parent_id', event.target.value)}
          >
            {parentResults.map((parent) => (
              <FormControlLabel
                key={parent.id}
                value={parent.id}
                control={<Radio />}
                label={parent.phone ? `${parent.full_name} · ${parent.phone}` : parent.full_name}
                disabled={submitting}
              />
            ))}
          </RadioGroup>
          {errors.parent_id ? <ErrorAlert message={errors.parent_id} /> : null}
          <RelationshipField
            value={values.relationship}
            onChange={(value) => setField('relationship', value)}
            disabled={submitting}
          />
        </Stack>
      ) : null}
      {mode === 'create' && values.parentMode === 'new' ? (
        <Stack spacing={1.5}>
          <TextField
            label={t('students:parentName')}
            value={values.parent_full_name}
            onChange={(event) => setField('parent_full_name', event.target.value)}
            required
            fullWidth
            error={Boolean(errors.parent_full_name || errors['parent_link.full_name'])}
            helperText={errors.parent_full_name || errors['parent_link.full_name']}
            disabled={submitting}
          />
          <TextField
            label={t('students:phone')}
            value={values.parent_phone}
            onChange={(event) => setField('parent_phone', event.target.value)}
            fullWidth
            error={Boolean(errors.parent_phone || errors['parent_link.phone'])}
            helperText={errors.parent_phone || errors['parent_link.phone']}
            disabled={submitting}
          />
          <TextField
            label={t('students:email')}
            type="email"
            value={values.parent_email}
            onChange={(event) => setField('parent_email', event.target.value)}
            fullWidth
            error={Boolean(errors.parent_email || errors['parent_link.email'])}
            helperText={errors.parent_email || errors['parent_link.email']}
            disabled={submitting}
          />
          <RelationshipField
            value={values.relationship}
            onChange={(value) => setField('relationship', value)}
            disabled={submitting}
          />
        </Stack>
      ) : null}
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
        <Button type="submit" variant="contained" disabled={submitting}>
          {submitting ? t('students:saving') : t('students:save')}
        </Button>
        <Button component={Link} to={studentId ? `/app/students/${studentId}` : '/app/students'} disabled={submitting}>
          {t('common:cancel')}
        </Button>
      </Stack>
    </Stack>
  )
}

function RelationshipField({
  value,
  onChange,
  disabled,
}: {
  value: string
  onChange: (value: string) => void
  disabled: boolean
}) {
  const { t } = useTranslation('students')
  return (
    <TextField select label={t('relationship')} value={value} onChange={(event) => onChange(event.target.value)} fullWidth disabled={disabled}>
      <MenuItem value="">{t('relationshipNone')}</MenuItem>
      <MenuItem value="mother">{t('relationshipMother')}</MenuItem>
      <MenuItem value="father">{t('relationshipFather')}</MenuItem>
      <MenuItem value="guardian">{t('relationshipGuardian')}</MenuItem>
      <MenuItem value="other">{t('relationshipOther')}</MenuItem>
    </TextField>
  )
}
