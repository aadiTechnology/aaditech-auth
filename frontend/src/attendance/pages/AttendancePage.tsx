import {
  Alert,
  Button,
  Chip,
  MenuItem,
  Stack,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from '@mui/material'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useSearchParams } from 'react-router-dom'

import { usePermission } from '../../access/hooks/usePermission'
import { messageForError } from '../../auth/validation/errors'
import { listBatches } from '../../batches/api'
import type { BatchListItem } from '../../batches/types'
import { ConfirmDialog } from '../../components/common/ConfirmDialog'
import { ErrorAlert } from '../../components/common/ErrorAlert'
import { LoadingScreen } from '../../components/common/LoadingScreen'
import { formatClock, formatDisplayDate } from '../../roster/format'
import { addDays, coachingToday } from '../../timetable/week'
import { getRoster, listAttendanceClasses, listHistory, listSummary, saveAttendance } from '../api'
import type { AttendanceClassItem, AttendanceStatus, ClassRoster, HistoryItem, SummaryItem } from '../types'

const STATUSES: AttendanceStatus[] = ['present', 'absent', 'late', 'excused']

interface Draft {
  status: AttendanceStatus | ''
  notes: string
  version: number | null
  savedStatus: AttendanceStatus | ''
  savedNotes: string
}

function draftsFrom(roster: ClassRoster) {
  return Object.fromEntries(
    roster.students.map((student) => {
      const status = student.attendance?.status ?? ''
      const notes = student.attendance?.notes ?? ''
      const draft: Draft = {
        status,
        notes,
        version: student.attendance?.version ?? null,
        savedStatus: status,
        savedNotes: notes,
      }
      return [student.student_id, draft]
    }),
  )
}

function isDirty(draft: Draft) {
  return draft.status !== draft.savedStatus || draft.notes !== draft.savedNotes
}

export function AttendancePage() {
  const { t } = useTranslation(['attendance', 'common'])
  const { hasPermission } = usePermission()
  const canUpdate = hasPermission('attendance.update')
  const [params, setParams] = useSearchParams()
  const batchId = params.get('batch') ?? ''
  const classId = params.get('class') ?? ''
  const today = coachingToday()
  const [fromDate, setFromDate] = useState(addDays(today, -14))
  const [toDate, setToDate] = useState(addDays(today, 14))
  const [historyFrom, setHistoryFrom] = useState(addDays(today, -30))
  const [historyTo, setHistoryTo] = useState(today)
  const [historyStudent, setHistoryStudent] = useState('')
  const [batches, setBatches] = useState<BatchListItem[]>([])
  const [classes, setClasses] = useState<AttendanceClassItem[]>([])
  const [roster, setRoster] = useState<ClassRoster | null>(null)
  const [drafts, setDrafts] = useState<Record<string, Draft>>({})
  const [history, setHistory] = useState<HistoryItem[] | null>(null)
  const [summary, setSummary] = useState<SummaryItem[] | null>(null)
  const [loadingRoster, setLoadingRoster] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [confirmAll, setConfirmAll] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)

  useEffect(() => {
    let cancelled = false
    listBatches({ status: 'all', limit: 100, sort: 'name' })
      .then((result) => {
        if (!cancelled) {
          setBatches(result.data.items)
        }
      })
      .catch((requestError: unknown) => {
        if (!cancelled) {
          setError(messageForError(requestError, t))
        }
      })
    return () => {
      cancelled = true
    }
  }, [t])

  useEffect(() => {
    if (!batchId) {
      setClasses([])
      setSummary(null)
      setHistory(null)
      return
    }
    let cancelled = false
    listAttendanceClasses({
      batch_id: batchId,
      from: fromDate,
      to: toDate,
      include_cancelled: true,
    })
      .then((result) => {
        if (!cancelled) {
          setClasses(result.data.items)
        }
      })
      .catch((requestError: unknown) => {
        if (!cancelled) {
          setError(messageForError(requestError, t))
        }
      })
    listSummary({ batch_id: batchId, from: historyFrom, to: historyTo })
      .then((result) => {
        if (!cancelled) {
          setSummary(result.data.items)
        }
      })
      .catch((requestError: unknown) => {
        if (!cancelled) {
          setSummary(null)
          setError(messageForError(requestError, t))
        }
      })
    listHistory({
      batch_id: batchId,
      from: historyFrom,
      to: historyTo,
      student_id: historyStudent || undefined,
    })
      .then((result) => {
        if (!cancelled) {
          setHistory(result.data.items)
        }
      })
      .catch((requestError: unknown) => {
        if (!cancelled) {
          setHistory(null)
          setError(messageForError(requestError, t))
        }
      })
    return () => {
      cancelled = true
    }
  }, [batchId, fromDate, toDate, historyFrom, historyTo, historyStudent, refreshKey, t])

  useEffect(() => {
    if (!classId) {
      setRoster(null)
      setDrafts({})
      return
    }
    let cancelled = false
    setLoadingRoster(true)
    getRoster(classId)
      .then((result) => {
        if (!cancelled) {
          setRoster(result.data)
          setDrafts(draftsFrom(result.data))
        }
      })
      .catch((requestError: unknown) => {
        if (!cancelled) {
          setRoster(null)
          setError(messageForError(requestError, t))
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoadingRoster(false)
        }
      })
    return () => {
      cancelled = true
    }
  }, [classId, refreshKey, t])

  function setBatch(value: string) {
    const next = new URLSearchParams(params)
    if (value) {
      next.set('batch', value)
    } else {
      next.delete('batch')
    }
    next.delete('class')
    setParams(next)
    setNotice('')
  }

  function setClass(value: string) {
    const next = new URLSearchParams(params)
    if (value) {
      next.set('class', value)
    } else {
      next.delete('class')
    }
    setParams(next)
    setNotice('')
  }

  function updateDraft(studentId: string, patch: Partial<Draft>) {
    setDrafts((current) => ({ ...current, [studentId]: { ...current[studentId], ...patch } }))
  }

  const dirty = Object.values(drafts).some(isDirty)
  const cancelledClass = roster?.class_status === 'cancelled'

  async function save() {
    if (!roster) {
      return
    }
    const marks = roster.students.flatMap((student) => {
      const draft = drafts[student.student_id]
      if (!draft || !draft.status || !isDirty(draft)) {
        return []
      }
      return [
        {
          student_id: student.student_id,
          status: draft.status,
          notes: draft.notes.trim() ? draft.notes.trim() : null,
          version: draft.version,
        },
      ]
    })
    if (marks.length === 0) {
      return
    }
    setSaving(true)
    setError('')
    try {
      const result = await saveAttendance(roster.id, marks)
      setRoster(result.data)
      setDrafts(draftsFrom(result.data))
      setNotice(t('attendance:saved'))
      setRefreshKey((current) => current + 1)
    } catch (requestError: unknown) {
      setError(messageForError(requestError, t))
    } finally {
      setSaving(false)
    }
  }

  const summaryRecorded = summary?.reduce((total, item) => total + item.recorded, 0) ?? 0

  return (
    <Stack spacing={3}>
      <Stack spacing={0.5}>
        <Typography variant="h2">{t('attendance:title')}</Typography>
        <Typography color="text.secondary">{t('attendance:description')}</Typography>
      </Stack>
      {notice ? <Alert severity="success">{notice}</Alert> : null}
      {error ? <ErrorAlert message={error} /> : null}
      <Stack direction={{ xs: 'column', md: 'row' }} spacing={1.5}>
        <TextField
          select
          label={t('attendance:batch')}
          value={batches.some((batch) => batch.id === batchId) ? batchId : ''}
          onChange={(event) => setBatch(event.target.value)}
          size="small"
          sx={{ minWidth: { md: 240 } }}
        >
          <MenuItem value="">{t('attendance:selectBatch')}</MenuItem>
          {batches.map((batch) => (
            <MenuItem key={batch.id} value={batch.id}>
              {batch.name} ({batch.batch_code})
            </MenuItem>
          ))}
        </TextField>
        <TextField
          type="date"
          label={t('attendance:from')}
          value={fromDate}
          onChange={(event) => setFromDate(event.target.value)}
          size="small"
          slotProps={{ inputLabel: { shrink: true } }}
        />
        <TextField
          type="date"
          label={t('attendance:to')}
          value={toDate}
          onChange={(event) => setToDate(event.target.value)}
          size="small"
          slotProps={{ inputLabel: { shrink: true } }}
        />
      </Stack>
      {!batchId ? <Typography>{t('attendance:selectBatchHint')}</Typography> : null}
      {batchId ? (
        <TextField
          select
          label={t('attendance:class')}
          value={classes.some((item) => item.id === classId) ? classId : ''}
          onChange={(event) => setClass(event.target.value)}
          size="small"
          sx={{ maxWidth: { md: 520 } }}
        >
          <MenuItem value="">{t('attendance:selectClass')}</MenuItem>
          {classes.map((item) => (
            <MenuItem key={item.id} value={item.id}>
              {formatDisplayDate(item.class_date)} {formatClock(item.start_time)}–{formatClock(item.end_time)}
              {item.topic ? ` · ${item.topic}` : ''}
              {item.class_status === 'cancelled' ? ` · ${t('attendance:cancelled')}` : ''}
            </MenuItem>
          ))}
        </TextField>
      ) : null}
      {batchId && classes.length === 0 ? <Typography>{t('attendance:emptyClasses')}</Typography> : null}
      {loadingRoster ? <LoadingScreen variant="section" /> : null}
      {roster ? (
        <Stack spacing={2}>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ alignItems: { sm: 'center' } }}>
            <Typography variant="subtitle1">
              {roster.batch_name} · {formatDisplayDate(roster.class_date)} {formatClock(roster.start_time)}–
              {formatClock(roster.end_time)}
            </Typography>
            <Chip label={t(`attendance:completion.${roster.completion}`)} />
          </Stack>
          <Typography color="text.secondary">
            {t('attendance:recordedCount', { recorded: roster.recorded_count, enrolled: roster.enrolled_count })}
          </Typography>
          {cancelledClass ? <Alert severity="info">{t('attendance:cancelledNotice')}</Alert> : null}
          {dirty ? <Alert severity="warning">{t('attendance:unsaved')}</Alert> : null}
          {roster.students.length === 0 ? <Typography>{t('attendance:emptyStudents')}</Typography> : null}
          {roster.students.map((student) => {
            const draft = drafts[student.student_id]
            const locked = !canUpdate || saving || (cancelledClass && !student.attendance)
            return (
              <Stack
                key={student.student_id}
                component="section"
                aria-label={student.full_name}
                spacing={1}
                sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2, p: 2 }}
              >
                <Typography variant="subtitle1">{student.full_name}</Typography>
                <Typography variant="body2" color="text.secondary">
                  {student.student_code}
                  {draft?.status ? '' : ` · ${t('attendance:notRecorded')}`}
                </Typography>
                <ToggleButtonGroup
                  exclusive
                  size="small"
                  value={draft?.status || null}
                  aria-label={t('attendance:statusFor', { name: student.full_name })}
                  onChange={(_, value: AttendanceStatus | null) => {
                    if (!value) {
                      return
                    }
                    updateDraft(student.student_id, { status: value })
                  }}
                  disabled={locked}
                  sx={{ flexWrap: 'wrap' }}
                >
                  {STATUSES.map((status) => (
                    <ToggleButton key={status} value={status}>
                      {t(`attendance:status.${status}`)}
                    </ToggleButton>
                  ))}
                </ToggleButtonGroup>
                <TextField
                  label={t('attendance:notes')}
                  value={draft?.notes ?? ''}
                  onChange={(event) => updateDraft(student.student_id, { notes: event.target.value })}
                  disabled={locked || !draft?.status}
                  size="small"
                  fullWidth
                  slotProps={{ htmlInput: { maxLength: 500 } }}
                />
              </Stack>
            )
          })}
          {canUpdate && roster.students.length > 0 ? (
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
              <Button variant="outlined" onClick={() => setConfirmAll(true)} disabled={saving || Boolean(cancelledClass)}>
                {t('attendance:markAll')}
              </Button>
              <Button variant="contained" onClick={() => void save()} disabled={!dirty || saving}>
                {saving ? t('attendance:saving') : t('attendance:save')}
              </Button>
              <Button
                onClick={() => {
                  if (roster) {
                    setDrafts(draftsFrom(roster))
                  }
                }}
                disabled={!dirty || saving}
              >
                {t('attendance:cancelChanges')}
              </Button>
            </Stack>
          ) : null}
        </Stack>
      ) : null}

      {batchId ? (
        <Stack spacing={1.5}>
          <Typography variant="h2">{t('attendance:summaryTitle')}</Typography>
          <Typography color="text.secondary">{t('attendance:formula')}</Typography>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5}>
            <TextField
              type="date"
              label={t('attendance:from')}
              value={historyFrom}
              onChange={(event) => setHistoryFrom(event.target.value)}
              size="small"
              slotProps={{ inputLabel: { shrink: true } }}
            />
            <TextField
              type="date"
              label={t('attendance:to')}
              value={historyTo}
              onChange={(event) => setHistoryTo(event.target.value)}
              size="small"
              slotProps={{ inputLabel: { shrink: true } }}
            />
            <TextField
              select
              label={t('attendance:student')}
              value={historyStudent}
              onChange={(event) => setHistoryStudent(event.target.value)}
              size="small"
              sx={{ minWidth: { sm: 220 } }}
            >
              <MenuItem value="">{t('attendance:allStudents')}</MenuItem>
              {(summary ?? []).map((item) => (
                <MenuItem key={item.student_id} value={item.student_id}>
                  {item.full_name}
                </MenuItem>
              ))}
            </TextField>
          </Stack>
          {summary && summaryRecorded === 0 ? <Typography>{t('attendance:summaryEmpty')}</Typography> : null}
          {summary && summaryRecorded > 0
            ? summary
                .filter((item) => !historyStudent || item.student_id === historyStudent)
                .map((item) => (
                  <Typography key={item.student_id}>
                    {item.full_name} ({item.student_code}):{' '}
                    {t('attendance:summaryLine', {
                      present: item.present,
                      absent: item.absent,
                      late: item.late,
                      excused: item.excused,
                      percentage: item.percentage == null ? t('attendance:noPercentage') : `${item.percentage}%`,
                    })}
                  </Typography>
                ))
            : null}
          <Typography variant="h2">{t('attendance:historyTitle')}</Typography>
          {history && history.length === 0 ? <Typography>{t('attendance:historyEmpty')}</Typography> : null}
          {history?.map((item) => (
            <Typography key={item.id}>
              {formatDisplayDate(item.class_date)} {formatClock(item.start_time)}–{formatClock(item.end_time)} ·{' '}
              {item.full_name} · {t(`attendance:status.${item.status}`)}
              {item.class_status === 'cancelled' ? ` · ${t('attendance:cancelled')}` : ''}
              {item.topic ? ` · ${item.topic}` : ''}
            </Typography>
          ))}
        </Stack>
      ) : null}

      <ConfirmDialog
        open={confirmAll}
        title={t('attendance:markAllTitle')}
        description={t('attendance:markAllBody')}
        confirmLabel={t('attendance:markAll')}
        onClose={() => setConfirmAll(false)}
        onConfirm={() => {
          setDrafts((current) =>
            Object.fromEntries(
              Object.entries(current).map(([id, draft]) => [id, { ...draft, status: 'present' as const }]),
            ),
          )
          setConfirmAll(false)
        }}
      />
    </Stack>
  )
}
