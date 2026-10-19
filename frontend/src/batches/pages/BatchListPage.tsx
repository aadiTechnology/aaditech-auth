import {
  Alert,
  Button,
  MenuItem,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TableSortLabel,
  TextField,
  Typography,
} from '@mui/material'
import { FormEvent, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useLocation } from 'react-router-dom'

import { usePermission } from '../../access/hooks/usePermission'
import { messageForError } from '../../auth/validation/errors'
import { ConfirmDialog } from '../../components/common/ConfirmDialog'
import { ErrorAlert } from '../../components/common/ErrorAlert'
import { LoadingScreen } from '../../components/common/LoadingScreen'
import { formatClock, formatDisplayDate } from '../../roster/format'
import { GRADES } from '../../students/types'
import { archiveBatch, listBatches } from '../api'
import type { BatchListData } from '../types'

const limit = 20

export function BatchListPage() {
  const { t } = useTranslation(['batches', 'common'])
  const { hasPermission } = usePermission()
  const location = useLocation()
  const [notice, setNotice] = useState((location.state as { notice?: string } | null)?.notice ?? '')
  const [query, setQuery] = useState('')
  const [subject, setSubject] = useState('')
  const [appliedQuery, setAppliedQuery] = useState('')
  const [appliedSubject, setAppliedSubject] = useState('')
  const [grade, setGrade] = useState('')
  const [status, setStatus] = useState('')
  const [sort, setSort] = useState<'name' | 'code' | 'subject' | 'grade' | 'status' | 'students'>('name')
  const [direction, setDirection] = useState<'asc' | 'desc'>('asc')
  const [offset, setOffset] = useState(0)
  const [refreshKey, setRefreshKey] = useState(0)
  const [data, setData] = useState<BatchListData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [archiveId, setArchiveId] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError('')
    listBatches({
      q: appliedQuery || undefined,
      subject: appliedSubject || undefined,
      grade: grade || undefined,
      status: status || undefined,
      sort,
      direction,
      limit,
      offset,
    })
      .then((result) => {
        if (!cancelled) {
          setData(result.data)
        }
      })
      .catch((requestError: unknown) => {
        if (!cancelled) {
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
  }, [appliedQuery, appliedSubject, grade, status, sort, direction, offset, refreshKey, t])

  function onSearch(event: FormEvent) {
    event.preventDefault()
    setOffset(0)
    setAppliedQuery(query.trim())
    setAppliedSubject(subject.trim())
  }

  function changeSort(next: typeof sort) {
    setOffset(0)
    if (sort === next) {
      setDirection((current) => (current === 'asc' ? 'desc' : 'asc'))
      return
    }
    setSort(next)
    setDirection('asc')
  }

  async function confirmArchive() {
    if (!archiveId || busy) {
      return
    }
    setBusy(true)
    setError('')
    try {
      await archiveBatch(archiveId)
      setNotice(t('batches:archived'))
      setArchiveId(null)
      setRefreshKey((current) => current + 1)
    } catch (requestError) {
      setError(messageForError(requestError, t))
      setArchiveId(null)
    } finally {
      setBusy(false)
    }
  }

  const total = data?.total ?? 0
  const page = Math.floor(offset / limit) + 1
  const pages = Math.max(1, Math.ceil(total / limit))
  const filtered = Boolean(appliedQuery || appliedSubject || grade || status)

  return (
    <Stack spacing={3}>
      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        spacing={2}
        sx={{ justifyContent: 'space-between', alignItems: { sm: 'center' } }}
      >
        <Stack spacing={0.5}>
          <Typography variant="h2">{t('batches:title')}</Typography>
          <Typography color="text.secondary">{t('batches:description')}</Typography>
        </Stack>
        {hasPermission('batches.create') ? (
          <Button component={Link} to="/app/batches/new" variant="contained">
            {t('batches:add')}
          </Button>
        ) : null}
      </Stack>
      {notice ? <Alert severity="success">{notice}</Alert> : null}
      {error ? <ErrorAlert message={error} /> : null}
      <Stack component="form" role="search" onSubmit={onSearch} direction={{ xs: 'column', md: 'row' }} spacing={1.5}>
        <TextField
          name="q"
          label={t('batches:searchLabel')}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          fullWidth
          size="small"
        />
        <TextField
          name="subject"
          label={t('batches:subject')}
          value={subject}
          onChange={(event) => setSubject(event.target.value)}
          size="small"
          sx={{ minWidth: { xs: '100%', md: 160 } }}
        />
        <TextField
          select
          label={t('batches:grade')}
          value={grade}
          onChange={(event) => {
            setOffset(0)
            setGrade(event.target.value)
          }}
          sx={{ minWidth: { xs: '100%', md: 140 } }}
          size="small"
        >
          <MenuItem value="">{t('batches:allGrades')}</MenuItem>
          {GRADES.map((item) => (
            <MenuItem key={item} value={item}>
              {t('batches:classOption', { grade: item })}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          select
          label={t('batches:status')}
          value={status}
          onChange={(event) => {
            setOffset(0)
            setStatus(event.target.value)
          }}
          sx={{ minWidth: { xs: '100%', md: 180 } }}
          size="small"
        >
          <MenuItem value="">{t('batches:statusCurrent')}</MenuItem>
          <MenuItem value="active">{t('batches:statusActive')}</MenuItem>
          <MenuItem value="inactive">{t('batches:statusInactive')}</MenuItem>
          <MenuItem value="archived">{t('batches:statusArchived')}</MenuItem>
          <MenuItem value="all">{t('batches:statusAll')}</MenuItem>
        </TextField>
        <Button type="submit" variant="outlined">
          {t('batches:search')}
        </Button>
      </Stack>
      {loading && !data ? <LoadingScreen variant="section" /> : null}
      {!loading && error && !data ? (
        <Button variant="outlined" onClick={() => setRefreshKey((current) => current + 1)}>
          {t('batches:retry')}
        </Button>
      ) : null}
      {data && data.items.length === 0 ? (
        <Typography>{filtered ? t('batches:emptyFiltered') : t('batches:empty')}</Typography>
      ) : null}
      {data && data.items.length > 0 ? (
        <TableContainer sx={{ overflowX: 'auto' }}>
          <Table aria-label={t('batches:listLabel')} size="small">
            <TableHead>
              <TableRow>
                <TableCell>
                  <TableSortLabel active={sort === 'code'} direction={sort === 'code' ? direction : 'asc'} onClick={() => changeSort('code')}>
                    {t('batches:code')}
                  </TableSortLabel>
                </TableCell>
                <TableCell>
                  <TableSortLabel active={sort === 'name'} direction={sort === 'name' ? direction : 'asc'} onClick={() => changeSort('name')}>
                    {t('batches:name')}
                  </TableSortLabel>
                </TableCell>
                <TableCell>
                  <TableSortLabel
                    active={sort === 'subject'}
                    direction={sort === 'subject' ? direction : 'asc'}
                    onClick={() => changeSort('subject')}
                  >
                    {t('batches:subject')}
                  </TableSortLabel>
                </TableCell>
                <TableCell sx={{ display: { xs: 'none', sm: 'table-cell' } }}>
                  <TableSortLabel active={sort === 'grade'} direction={sort === 'grade' ? direction : 'asc'} onClick={() => changeSort('grade')}>
                    {t('batches:grade')}
                  </TableSortLabel>
                </TableCell>
                <TableCell>
                  <TableSortLabel
                    active={sort === 'students'}
                    direction={sort === 'students' ? direction : 'asc'}
                    onClick={() => changeSort('students')}
                  >
                    {t('batches:students')}
                  </TableSortLabel>
                </TableCell>
                <TableCell sx={{ display: { xs: 'none', md: 'table-cell' } }}>{t('batches:schedule')}</TableCell>
                <TableCell>
                  <TableSortLabel
                    active={sort === 'status'}
                    direction={sort === 'status' ? direction : 'asc'}
                    onClick={() => changeSort('status')}
                  >
                    {t('batches:status')}
                  </TableSortLabel>
                </TableCell>
                <TableCell>{t('batches:actions')}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {data.items.map((batch) => (
                <TableRow key={batch.id} hover>
                  <TableCell>{batch.batch_code}</TableCell>
                  <TableCell>{batch.name}</TableCell>
                  <TableCell>{batch.subject || t('batches:notProvided')}</TableCell>
                  <TableCell sx={{ display: { xs: 'none', sm: 'table-cell' } }}>
                    {batch.grade ? t('batches:classOption', { grade: batch.grade }) : t('batches:notProvided')}
                  </TableCell>
                  <TableCell>{batch.student_count}</TableCell>
                  <TableCell sx={{ display: { xs: 'none', md: 'table-cell' } }}>
                    {batch.next_class
                      ? `${formatDisplayDate(batch.next_class.class_date)} ${formatClock(batch.next_class.start_time)}`
                      : t('batches:noSchedule')}
                  </TableCell>
                  <TableCell>{t(`batches:status${statusKey(batch.status)}`)}</TableCell>
                  <TableCell>
                    <Stack direction={{ xs: 'column', lg: 'row' }} spacing={1}>
                      <Button component={Link} to={`/app/batches/${batch.id}`} size="small">
                        {t('batches:view')}
                      </Button>
                      {hasPermission('batches.update') && batch.status !== 'archived' ? (
                        <Button component={Link} to={`/app/batches/${batch.id}/edit`} size="small">
                          {t('batches:edit')}
                        </Button>
                      ) : null}
                      {hasPermission('batches.archive') && batch.status !== 'archived' ? (
                        <Button size="small" color="error" onClick={() => setArchiveId(batch.id)}>
                          {t('batches:archive')}
                        </Button>
                      ) : null}
                    </Stack>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      ) : null}
      {data && total > limit ? (
        <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
          <Button variant="outlined" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - limit))}>
            {t('batches:previous')}
          </Button>
          <Typography>{t('batches:page', { page, pages })}</Typography>
          <Button variant="outlined" disabled={offset + limit >= total} onClick={() => setOffset(offset + limit)}>
            {t('batches:next')}
          </Button>
        </Stack>
      ) : null}
      <ConfirmDialog
        open={Boolean(archiveId)}
        title={t('batches:confirmArchiveTitle')}
        description={t('batches:confirmArchiveBody')}
        confirmLabel={t('batches:archive')}
        busy={busy}
        onClose={() => setArchiveId(null)}
        onConfirm={() => void confirmArchive()}
      />
    </Stack>
  )
}

function statusKey(status: string) {
  return `${status.charAt(0).toUpperCase()}${status.slice(1)}`
}
