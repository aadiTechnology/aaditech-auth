import { Alert, Box, Button, Checkbox, FormControlLabel, MenuItem, Stack, TextField, Typography } from '@mui/material'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useSearchParams } from 'react-router-dom'

import { usePermission } from '../../access/hooks/usePermission'
import { messageForError } from '../../auth/validation/errors'
import { ErrorAlert } from '../../components/common/ErrorAlert'
import { LoadingScreen } from '../../components/common/LoadingScreen'
import { formatClock, formatDisplayDate, isIsoDate } from '../../roster/format'
import { listBatches } from '../../batches/api'
import type { BatchListItem } from '../../batches/types'
import { MeetJoinLink } from '../../meet/components/MeetJoinLink'
import { MeetLinkDialog } from '../../meet/components/MeetLinkDialog'
import { ClassDialog } from '../components/ClassDialog'
import { listClasses } from '../api'
import type { ScheduledClassItem } from '../types'
import { addDays, coachingToday, startOfWeek, weekDates } from '../week'

export function TimetablePage() {
  const { t } = useTranslation(['timetable', 'meet', 'common'])
  const { hasPermission } = usePermission()
  const [params, setParams] = useSearchParams()
  const focus = params.get('date')
  const weekStart = startOfWeek(focus && isIsoDate(focus) ? focus : coachingToday())
  const batchId = params.get('batch') ?? ''
  const days = weekDates(weekStart)
  const today = coachingToday()
  const [batches, setBatches] = useState<BatchListItem[]>([])
  const [items, setItems] = useState<ScheduledClassItem[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [showCancelled, setShowCancelled] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [meetClassId, setMeetClassId] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    listBatches({ status: 'all', limit: 100, sort: 'name' })
      .then((result) => {
        if (!cancelled) {
          setBatches(result.data.items)
        }
      })
      .catch(() => {
        if (!cancelled) {
          setBatches([])
        }
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError('')
    listClasses({
      from: weekStart,
      to: addDays(weekStart, 6),
      batch_id: batchId || undefined,
      include_cancelled: showCancelled,
    })
      .then((result) => {
        if (!cancelled) {
          setItems(result.data.items)
        }
      })
      .catch((requestError: unknown) => {
        if (!cancelled) {
          setItems(null)
          setError(messageForError(requestError, t))
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
  }, [weekStart, batchId, showCancelled, refreshKey, t])

  function setWeek(date: string) {
    const next = new URLSearchParams(params)
    next.set('date', date)
    setParams(next)
  }

  function setBatch(value: string) {
    const next = new URLSearchParams(params)
    if (value) {
      next.set('batch', value)
    } else {
      next.delete('batch')
    }
    setParams(next)
  }

  const visibleBatches = batches.filter((batch) => batch.status !== 'archived' || batch.id === batchId)

  return (
    <Stack spacing={3}>
      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        spacing={2}
        sx={{ justifyContent: 'space-between', alignItems: { sm: 'center' } }}
      >
        <Stack spacing={0.5}>
          <Typography variant="h2">{t('timetable:title')}</Typography>
          <Typography color="text.secondary">{t('timetable:description')}</Typography>
        </Stack>
        {hasPermission('timetable.create') ? (
          <Button
            variant="contained"
            onClick={() => {
              setEditingId(null)
              setDialogOpen(true)
            }}
          >
            {t('timetable:add')}
          </Button>
        ) : null}
      </Stack>
      {notice ? <Alert severity="success">{notice}</Alert> : null}
      {error ? <ErrorAlert message={error} /> : null}
      <Stack direction={{ xs: 'column', md: 'row' }} spacing={1.5} sx={{ alignItems: { md: 'center' } }}>
        <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap' }}>
          <Button variant="outlined" onClick={() => setWeek(addDays(weekStart, -7))}>
            {t('timetable:previousWeek')}
          </Button>
          <Button variant="outlined" onClick={() => setWeek(coachingToday())}>
            {t('timetable:thisWeek')}
          </Button>
          <Button variant="outlined" onClick={() => setWeek(addDays(weekStart, 7))}>
            {t('timetable:nextWeek')}
          </Button>
        </Stack>
        <Typography>
          {t('timetable:weekOf', {
            start: formatDisplayDate(weekStart),
            end: formatDisplayDate(addDays(weekStart, 6)),
          })}
        </Typography>
      </Stack>
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5} sx={{ alignItems: { sm: 'center' } }}>
        <TextField
          select
          label={t('timetable:batch')}
          value={batchId}
          onChange={(event) => setBatch(event.target.value)}
          size="small"
          sx={{ minWidth: { xs: '100%', sm: 240 } }}
        >
          <MenuItem value="">{t('timetable:allBatches')}</MenuItem>
          {visibleBatches.map((batch) => (
            <MenuItem key={batch.id} value={batch.id}>
              {batch.name} ({batch.batch_code})
            </MenuItem>
          ))}
        </TextField>
        <FormControlLabel
          control={<Checkbox checked={showCancelled} onChange={(event) => setShowCancelled(event.target.checked)} />}
          label={t('timetable:showCancelled')}
        />
      </Stack>
      {loading && !items ? <LoadingScreen variant="section" /> : null}
      {!loading && error && !items ? (
        <Button variant="outlined" onClick={() => setRefreshKey((current) => current + 1)}>
          {t('timetable:retry')}
        </Button>
      ) : null}
      {items && items.length === 0 ? <Typography>{t('timetable:empty')}</Typography> : null}
      {items ? (
        <Box
          sx={{
            display: 'grid',
            gap: 1,
            gridTemplateColumns: { xs: '1fr', md: 'repeat(7, minmax(0, 1fr))' },
          }}
        >
          {days.map((day, index) => {
            const dayItems = items.filter((item) => item.class_date === day)
            return (
              <Stack
                key={day}
                component="section"
                aria-label={`${t(`timetable:daysLong.${index}`)} ${formatDisplayDate(day)}`}
                spacing={1}
                sx={{
                  border: '1px solid',
                  borderColor: 'divider',
                  borderRadius: 2,
                  p: 1,
                  minHeight: { md: 180 },
                  bgcolor: day === today ? 'action.hover' : 'background.paper',
                }}
              >
                <Typography variant="subtitle2">
                  {t(`timetable:days.${index}`)}
                  {day === today ? ` · ${t('timetable:today')}` : ''}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {formatDisplayDate(day)}
                </Typography>
                {dayItems.length === 0 ? (
                  <Typography variant="body2" color="text.secondary">
                    {t('timetable:emptyDay')}
                  </Typography>
                ) : null}
                {dayItems.map((item) => (
                  <Stack key={item.id} spacing={0.5}>
                    <Button
                      variant="outlined"
                      onClick={() => {
                        setEditingId(item.id)
                        setDialogOpen(true)
                      }}
                      sx={{
                        justifyContent: 'flex-start',
                        textAlign: 'left',
                        textTransform: 'none',
                        textDecoration: item.status === 'cancelled' ? 'line-through' : 'none',
                      }}
                    >
                      <Stack spacing={0.25} sx={{ alignItems: 'flex-start' }}>
                        <Typography variant="body2">
                          {formatClock(item.start_time)}–{formatClock(item.end_time)}
                        </Typography>
                        <Typography variant="body2">{item.batch_name}</Typography>
                        {item.topic ? <Typography variant="caption">{item.topic}</Typography> : null}
                        <Typography variant="caption">
                          {item.meet_status === 'added' ? t('meet:linkAdded') : t('meet:linkMissing')}
                        </Typography>
                        {item.status === 'cancelled' ? (
                          <Typography variant="caption">{t('timetable:statusCancelled')}</Typography>
                        ) : null}
                      </Stack>
                    </Button>
                    <Stack direction="row" spacing={0.5} sx={{ flexWrap: 'wrap' }}>
                      <MeetJoinLink url={item.meet_url} label={t('meet:join')} />
                      {hasPermission('meet.update') && item.status !== 'cancelled' ? (
                        <Button size="small" onClick={() => setMeetClassId(item.id)}>
                          {item.meet_url ? t('meet:editLink') : t('meet:addLink')}
                        </Button>
                      ) : null}
                    </Stack>
                  </Stack>
                ))}
              </Stack>
            )
          })}
        </Box>
      ) : null}
      <ClassDialog
        open={dialogOpen}
        classId={editingId}
        batches={batches}
        defaultDate={days.includes(today) ? today : weekStart}
        defaultBatchId={batchId}
        onClose={() => setDialogOpen(false)}
        onSaved={(message) => {
          setNotice(message)
          setRefreshKey((current) => current + 1)
        }}
      />
      <MeetLinkDialog
        open={Boolean(meetClassId)}
        classId={meetClassId}
        onClose={() => setMeetClassId(null)}
        onSaved={(message) => {
          setNotice(message)
          setRefreshKey((current) => current + 1)
        }}
      />
    </Stack>
  )
}
