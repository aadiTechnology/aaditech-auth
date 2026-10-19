import { Alert, Button, MenuItem, Stack, TextField, Typography } from '@mui/material'
import { FormEvent, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'

import { usePermission } from '../../access/hooks/usePermission'
import { messageForError } from '../../auth/validation/errors'
import { ConfirmDialog } from '../../components/common/ConfirmDialog'
import { ErrorAlert } from '../../components/common/ErrorAlert'
import { LoadingScreen } from '../../components/common/LoadingScreen'
import { formatClock, formatDisplayDate } from '../../roster/format'
import { ApiError } from '../../services/api/errors'
import { listStudents } from '../../students/api'
import type { StudentListItem } from '../../students/types'
import { listClasses } from '../../timetable/api'
import type { ScheduledClassItem } from '../../timetable/types'
import { addDays, coachingToday } from '../../timetable/week'
import { archiveBatch, assignStudents, getBatch, removeStudent } from '../api'
import type { BatchDetail } from '../types'

export function BatchDetailPage() {
  const { batchId = '' } = useParams()
  const { t } = useTranslation(['batches', 'common'])
  const { hasPermission } = usePermission()
  const navigate = useNavigate()
  const location = useLocation()
  const [notice, setNotice] = useState((location.state as { notice?: string } | null)?.notice ?? '')
  const [batch, setBatch] = useState<BatchDetail | null>(null)
  const [classes, setClasses] = useState<ScheduledClassItem[]>([])
  const [loading, setLoading] = useState(true)
  const [missing, setMissing] = useState(false)
  const [error, setError] = useState('')
  const [archiveOpen, setArchiveOpen] = useState(false)
  const [removeId, setRemoveId] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [studentQuery, setStudentQuery] = useState('')
  const [studentResults, setStudentResults] = useState<StudentListItem[]>([])
  const [studentId, setStudentId] = useState('')
  const canUpdate = hasPermission('batches.update')
  const canReadStudents = hasPermission('students.read')
  const canReadTimetable = hasPermission('timetable.read')

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setMissing(false)
    setError('')
    getBatch(batchId)
      .then(async (result) => {
        if (cancelled) {
          return
        }
        setBatch(result.data)
        if (canReadTimetable) {
          const today = coachingToday()
          const schedule = await listClasses({
            from: today,
            to: addDays(today, 41),
            batch_id: batchId,
          })
          if (!cancelled) {
            setClasses(schedule.data.items.slice(0, 8))
          }
        }
      })
      .catch((requestError: unknown) => {
        if (!cancelled) {
          if (requestError instanceof ApiError && requestError.status === 404) {
            setMissing(true)
          } else {
            setError(messageForError(requestError, t))
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
  }, [batchId, canReadTimetable, t])

  async function confirmArchive() {
    setBusy(true)
    try {
      await archiveBatch(batchId)
      navigate('/app/batches', { state: { notice: t('batches:archived') } })
    } catch (requestError) {
      setError(messageForError(requestError, t))
      setArchiveOpen(false)
    } finally {
      setBusy(false)
    }
  }

  async function searchStudents() {
    setBusy(true)
    setError('')
    try {
      const result = await listStudents({ q: studentQuery.trim(), status: 'active', limit: 20 })
      const assigned = new Set(batch?.students.map((student) => student.id))
      setStudentResults(result.data.items.filter((student) => !assigned.has(student.id)))
    } catch (requestError) {
      setError(messageForError(requestError, t))
    } finally {
      setBusy(false)
    }
  }

  async function onAssign(event: FormEvent) {
    event.preventDefault()
    if (!studentId || busy) {
      return
    }
    setBusy(true)
    setError('')
    try {
      const result = await assignStudents(batchId, [studentId])
      setBatch(result.data)
      setNotice(t('batches:assigned'))
      setStudentId('')
      setStudentResults([])
    } catch (requestError) {
      setError(messageForError(requestError, t))
    } finally {
      setBusy(false)
    }
  }

  async function confirmRemove() {
    if (!removeId) {
      return
    }
    setBusy(true)
    try {
      const result = await removeStudent(batchId, removeId)
      setBatch(result.data)
      setNotice(t('batches:removed'))
      setRemoveId(null)
    } catch (requestError) {
      setError(messageForError(requestError, t))
      setRemoveId(null)
    } finally {
      setBusy(false)
    }
  }

  if (loading) {
    return <LoadingScreen variant="section" />
  }
  if (missing || !batch) {
    return (
      <Stack spacing={2}>
        <Typography>{missing ? t('batches:notFound') : error}</Typography>
        <Button component={Link} to="/app/batches" variant="outlined">
          {t('batches:back')}
        </Button>
      </Stack>
    )
  }

  return (
    <Stack spacing={3} sx={{ maxWidth: 800 }}>
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
        <Button component={Link} to="/app/batches" variant="outlined">
          {t('batches:back')}
        </Button>
        {canUpdate && batch.status !== 'archived' ? (
          <Button component={Link} to={`/app/batches/${batch.id}/edit`} variant="contained">
            {t('batches:edit')}
          </Button>
        ) : null}
        {canReadTimetable ? (
          <Button component={Link} to={`/app/timetable?batch=${batch.id}`} variant="outlined">
            {t('batches:viewTimetable')}
          </Button>
        ) : null}
        {hasPermission('batches.archive') && batch.status !== 'archived' ? (
          <Button color="error" variant="outlined" onClick={() => setArchiveOpen(true)}>
            {t('batches:archive')}
          </Button>
        ) : null}
      </Stack>
      {notice ? <Alert severity="success">{notice}</Alert> : null}
      {error ? <ErrorAlert message={error} /> : null}
      <Stack spacing={0.5}>
        <Typography variant="h2">{batch.name}</Typography>
        <Typography color="text.secondary">
          {t('batches:code')}: {batch.batch_code}
        </Typography>
      </Stack>
      <DetailRow label={t('batches:status')} value={t(`batches:status${statusKey(batch.status)}`)} />
      <DetailRow label={t('batches:subject')} value={batch.subject} />
      <DetailRow label={t('batches:grade')} value={batch.grade ? t('batches:classOption', { grade: batch.grade }) : null} />
      <DetailRow label={t('batches:descriptionField')} value={batch.description} />
      <DetailRow label={t('batches:students')} value={String(batch.student_count)} />
      <DetailRow
        label={t('batches:schedule')}
        value={
          batch.next_class
            ? `${formatDisplayDate(batch.next_class.class_date)} ${formatClock(batch.next_class.start_time)}–${formatClock(batch.next_class.end_time)}`
            : t('batches:noSchedule')
        }
      />
      {canReadTimetable ? (
        <Stack spacing={1}>
          <Typography variant="h2">{t('batches:scheduleHeading')}</Typography>
          {classes.length === 0 ? <Typography>{t('batches:noUpcoming')}</Typography> : null}
          {classes.map((item) => (
            <Typography key={item.id}>
              {formatDisplayDate(item.class_date)} {formatClock(item.start_time)}–{formatClock(item.end_time)}
              {item.topic ? ` — ${item.topic}` : ''}
            </Typography>
          ))}
        </Stack>
      ) : null}
      <Typography variant="h2">{t('batches:assignedStudents')}</Typography>
      {batch.students.length === 0 ? <Typography>{t('batches:noStudents')}</Typography> : null}
      {batch.students.map((student) => (
        <Stack key={student.id} spacing={0.5} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2, p: 2 }}>
          {canReadStudents ? (
            <Button component={Link} to={`/app/students/${student.id}`} sx={{ alignSelf: 'flex-start', px: 0 }}>
              {student.full_name}
            </Button>
          ) : (
            <Typography fontWeight={700}>{student.full_name}</Typography>
          )}
          <Typography>
            {student.student_code}
            {student.grade ? ` · ${t('batches:classOption', { grade: student.grade })}` : ''}
          </Typography>
          {canUpdate ? (
            <Button color="error" sx={{ alignSelf: 'flex-start' }} onClick={() => setRemoveId(student.id)}>
              {t('batches:remove')}
            </Button>
          ) : null}
        </Stack>
      ))}
      {canUpdate && canReadStudents && batch.status !== 'archived' ? (
        <Stack component="form" spacing={1.5} onSubmit={onAssign}>
          <Typography fontWeight={700}>{t('batches:assignStudent')}</Typography>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
            <TextField
              label={t('batches:studentSearch')}
              value={studentQuery}
              onChange={(event) => setStudentQuery(event.target.value)}
              fullWidth
              size="small"
            />
            <Button type="button" variant="outlined" onClick={() => void searchStudents()} disabled={busy}>
              {t('batches:search')}
            </Button>
          </Stack>
          <TextField select label={t('batches:chooseStudent')} value={studentId} onChange={(event) => setStudentId(event.target.value)} fullWidth>
            <MenuItem value="">{t('batches:chooseStudent')}</MenuItem>
            {studentResults.map((student) => (
              <MenuItem key={student.id} value={student.id}>
                {student.full_name} ({student.student_code})
              </MenuItem>
            ))}
          </TextField>
          <Button type="submit" variant="contained" disabled={!studentId || busy} sx={{ alignSelf: 'flex-start' }}>
            {t('batches:assignStudent')}
          </Button>
        </Stack>
      ) : null}
      <ConfirmDialog
        open={archiveOpen}
        title={t('batches:confirmArchiveTitle')}
        description={t('batches:confirmArchiveBody')}
        confirmLabel={t('batches:archive')}
        busy={busy}
        onClose={() => setArchiveOpen(false)}
        onConfirm={() => void confirmArchive()}
      />
      <ConfirmDialog
        open={Boolean(removeId)}
        title={t('batches:confirmRemoveTitle')}
        description={t('batches:confirmRemoveBody')}
        confirmLabel={t('batches:remove')}
        busy={busy}
        onClose={() => setRemoveId(null)}
        onConfirm={() => void confirmRemove()}
      />
    </Stack>
  )
}

function DetailRow({ label, value }: { label: string; value: string | null | undefined }) {
  const { t } = useTranslation('batches')
  return (
    <Typography>
      {label}: {value?.trim() ? value : t('notProvided')}
    </Typography>
  )
}

function statusKey(status: string) {
  return `${status.charAt(0).toUpperCase()}${status.slice(1)}`
}
