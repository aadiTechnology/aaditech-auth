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
import { archiveParent, listParents } from '../api'
import type { ParentListData } from '../types'

const limit = 20

export function ParentListPage() {
  const { t } = useTranslation(['parents', 'common'])
  const { hasPermission } = usePermission()
  const location = useLocation()
  const [notice, setNotice] = useState((location.state as { notice?: string } | null)?.notice ?? '')
  const [query, setQuery] = useState('')
  const [appliedQuery, setAppliedQuery] = useState('')
  const [status, setStatus] = useState('')
  const [sort, setSort] = useState<'name' | 'phone' | 'status'>('name')
  const [direction, setDirection] = useState<'asc' | 'desc'>('asc')
  const [offset, setOffset] = useState(0)
  const [refreshKey, setRefreshKey] = useState(0)
  const [data, setData] = useState<ParentListData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [archiveId, setArchiveId] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError('')
    listParents({
      q: appliedQuery || undefined,
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
  }, [appliedQuery, status, sort, direction, offset, refreshKey, t])

  function onSearch(event: FormEvent) {
    event.preventDefault()
    setOffset(0)
    setAppliedQuery(query.trim())
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
    if (!archiveId) {
      return
    }
    setBusy(true)
    try {
      await archiveParent(archiveId)
      setNotice(t('parents:archived'))
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
  const filtered = Boolean(appliedQuery || status)

  return (
    <Stack spacing={3}>
      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        spacing={2}
        sx={{ justifyContent: 'space-between', alignItems: { sm: 'center' } }}
      >
        <Stack spacing={0.5}>
          <Typography variant="h2">{t('parents:title')}</Typography>
          <Typography color="text.secondary">{t('parents:description')}</Typography>
        </Stack>
        {hasPermission('parents.create') ? (
          <Button component={Link} to="/app/parents/new" variant="contained">
            {t('parents:add')}
          </Button>
        ) : null}
      </Stack>
      {notice ? <Alert severity="success">{notice}</Alert> : null}
      {error ? <ErrorAlert message={error} /> : null}
      <Stack component="form" role="search" onSubmit={onSearch} direction={{ xs: 'column', sm: 'row' }} spacing={1.5}>
        <TextField
          name="q"
          label={t('parents:searchLabel')}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          fullWidth
          size="small"
        />
        <TextField
          select
          label={t('parents:status')}
          value={status}
          onChange={(event) => {
            setOffset(0)
            setStatus(event.target.value)
          }}
          sx={{ minWidth: { xs: '100%', sm: 200 } }}
          size="small"
        >
          <MenuItem value="">{t('parents:statusCurrent')}</MenuItem>
          <MenuItem value="active">{t('parents:statusActive')}</MenuItem>
          <MenuItem value="archived">{t('parents:statusArchived')}</MenuItem>
          <MenuItem value="all">{t('parents:statusAll')}</MenuItem>
        </TextField>
        <Button type="submit" variant="outlined">
          {t('parents:search')}
        </Button>
      </Stack>
      {loading && !data ? <LoadingScreen variant="section" /> : null}
      {!loading && error && !data ? (
        <Button variant="outlined" onClick={() => setRefreshKey((current) => current + 1)}>
          {t('parents:retry')}
        </Button>
      ) : null}
      {data && data.items.length === 0 ? (
        <Typography>{filtered ? t('parents:emptyFiltered') : t('parents:empty')}</Typography>
      ) : null}
      {data && data.items.length > 0 ? (
        <TableContainer sx={{ overflowX: 'auto' }}>
          <Table aria-label={t('parents:listLabel')} size="small">
            <TableHead>
              <TableRow>
                <TableCell>
                  <TableSortLabel active={sort === 'name'} direction={sort === 'name' ? direction : 'asc'} onClick={() => changeSort('name')}>
                    {t('parents:fullName')}
                  </TableSortLabel>
                </TableCell>
                <TableCell>
                  <TableSortLabel active={sort === 'phone'} direction={sort === 'phone' ? direction : 'asc'} onClick={() => changeSort('phone')}>
                    {t('parents:phone')}
                  </TableSortLabel>
                </TableCell>
                <TableCell sx={{ display: { xs: 'none', md: 'table-cell' } }}>{t('parents:email')}</TableCell>
                <TableCell>{t('parents:students')}</TableCell>
                <TableCell>
                  <TableSortLabel active={sort === 'status'} direction={sort === 'status' ? direction : 'asc'} onClick={() => changeSort('status')}>
                    {t('parents:status')}
                  </TableSortLabel>
                </TableCell>
                <TableCell>{t('parents:actions')}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {data.items.map((parent) => (
                <TableRow key={parent.id} hover>
                  <TableCell>{parent.full_name}</TableCell>
                  <TableCell>{parent.phone || t('parents:notProvided')}</TableCell>
                  <TableCell sx={{ display: { xs: 'none', md: 'table-cell' } }}>
                    {parent.email || t('parents:notProvided')}
                  </TableCell>
                  <TableCell>
                    {parent.students.length > 0
                      ? parent.students.map((student) => student.full_name).join(', ')
                      : t('parents:notProvided')}
                  </TableCell>
                  <TableCell>{t(`parents:status${statusKey(parent.status)}`)}</TableCell>
                  <TableCell>
                    <Stack direction={{ xs: 'column', lg: 'row' }} spacing={1}>
                      <Button component={Link} to={`/app/parents/${parent.id}`} size="small">
                        {t('parents:view')}
                      </Button>
                      {hasPermission('parents.update') ? (
                        <Button component={Link} to={`/app/parents/${parent.id}/edit`} size="small">
                          {t('parents:edit')}
                        </Button>
                      ) : null}
                      {hasPermission('parents.archive') && parent.status !== 'archived' ? (
                        <Button size="small" color="error" onClick={() => setArchiveId(parent.id)}>
                          {t('parents:archive')}
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
            {t('parents:previous')}
          </Button>
          <Typography>{t('parents:page', { page, pages })}</Typography>
          <Button variant="outlined" disabled={offset + limit >= total} onClick={() => setOffset(offset + limit)}>
            {t('parents:next')}
          </Button>
        </Stack>
      ) : null}
      <ConfirmDialog
        open={Boolean(archiveId)}
        title={t('parents:confirmArchiveTitle')}
        description={t('parents:confirmArchiveBody')}
        confirmLabel={t('parents:archive')}
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
