import { Alert, Button, MenuItem, Stack, TextField, Typography } from '@mui/material'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { usePermission } from '../../access/hooks/usePermission'
import { messageForError } from '../../auth/validation/errors'
import { listBatches } from '../../batches/api'
import type { BatchListItem } from '../../batches/types'
import { ErrorAlert } from '../../components/common/ErrorAlert'
import { LoadingScreen } from '../../components/common/LoadingScreen'
import { formatClock, formatDisplayDate } from '../../roster/format'
import { addDays, coachingToday } from '../../timetable/week'
import type { ScheduledClassItem } from '../../timetable/types'
import { listUpcomingMeetings } from '../api'
import { MeetJoinLink } from '../components/MeetJoinLink'
import { MeetLinkDialog } from '../components/MeetLinkDialog'

export function MeetPage() {
  const { t } = useTranslation(['meet', 'common'])
  const { hasPermission } = usePermission()
  const canEdit = hasPermission('meet.update')
  const today = coachingToday()
  const [batches, setBatches] = useState<BatchListItem[]>([])
  const [batchId, setBatchId] = useState('')
  const [items, setItems] = useState<ScheduledClassItem[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [refreshKey, setRefreshKey] = useState(0)
  const [editingId, setEditingId] = useState<string | null>(null)

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
    listUpcomingMeetings({
      from: today,
      to: addDays(today, 14),
      batch_id: batchId || undefined,
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
  }, [batchId, refreshKey, t, today])

  return (
    <Stack spacing={3}>
      <Stack spacing={0.5}>
        <Typography variant="h2">{t('meet:title')}</Typography>
        <Typography color="text.secondary">{t('meet:description')}</Typography>
      </Stack>
      {notice ? <Alert severity="success">{notice}</Alert> : null}
      {error ? <ErrorAlert message={error} /> : null}
      <TextField
        select
        label={t('meet:batch')}
        value={batchId}
        onChange={(event) => setBatchId(event.target.value)}
        size="small"
        sx={{ maxWidth: { sm: 320 } }}
      >
        <MenuItem value="">{t('meet:allBatches')}</MenuItem>
        {batches
          .filter((batch) => batch.status !== 'archived')
          .map((batch) => (
            <MenuItem key={batch.id} value={batch.id}>
              {batch.name} ({batch.batch_code})
            </MenuItem>
          ))}
      </TextField>
      {loading && !items ? <LoadingScreen variant="section" /> : null}
      {!loading && error && !items ? (
        <Button variant="outlined" onClick={() => setRefreshKey((current) => current + 1)}>
          {t('meet:retry')}
        </Button>
      ) : null}
      {items && items.length === 0 ? <Typography>{t('meet:empty')}</Typography> : null}
      {items?.map((item) => (
        <Stack
          key={item.id}
          component="section"
          aria-label={item.batch_name}
          spacing={1}
          sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2, p: 2 }}
        >
          <Typography variant="subtitle1">{item.batch_name}</Typography>
          <Typography color="text.secondary">
            {formatDisplayDate(item.class_date)} · {formatClock(item.start_time)}–{formatClock(item.end_time)}
            {item.topic ? ` · ${item.topic}` : ''}
          </Typography>
          <Typography>{item.meet_status === 'added' ? t('meet:linkAdded') : t('meet:linkMissing')}</Typography>
          {item.meet_status !== 'added' ? (
            <Typography variant="body2" color="text.secondary">
              {t('meet:missingMessage')}
            </Typography>
          ) : null}
          <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap' }}>
            <MeetJoinLink url={item.meet_url} label={t('meet:join')} />
            {canEdit ? (
              <Button variant="outlined" size="small" onClick={() => setEditingId(item.id)}>
                {item.meet_url ? t('meet:editLink') : t('meet:addLink')}
              </Button>
            ) : null}
          </Stack>
        </Stack>
      ))}
      <MeetLinkDialog
        open={Boolean(editingId)}
        classId={editingId}
        onClose={() => setEditingId(null)}
        onSaved={(message) => {
          setNotice(message)
          setRefreshKey((current) => current + 1)
        }}
      />
    </Stack>
  )
}
