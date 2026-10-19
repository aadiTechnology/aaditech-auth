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
import { ConfirmDialog } from '../../components/common/ConfirmDialog'
import { ErrorAlert } from '../../components/common/ErrorAlert'
import { LoadingScreen } from '../../components/common/LoadingScreen'
import { formatDisplayDate } from '../../roster/format'
import { messageForError } from '../../auth/validation/errors'
import { archiveStudent, listStudents } from '../api'
import { GRADES, type StudentListData } from '../types'

const limit = 20

export function StudentListPage() {
  const { t } = useTranslation(['students', 'common'])
  const { hasPermission } = usePermission()
  const location = useLocation()
  const [notice, setNotice] = useState((location.state as { notice?: string } | null)?.notice ?? '')
  const [query, setQuery] = useState('')
  const [appliedQuery, setAppliedQuery] = useState('')
  const [grade, setGrade] = useState('')
  const [status, setStatus] = useState('')
  const [sort, setSort] = useState<'name' | 'code' | 'grade' | 'status' | 'enrollment'>('name')
  const [direction, setDirection] = useState<'asc' | 'desc'>('asc')
  const [offset, setOffset] = useState(0)
  const [refreshKey, setRefreshKey] = useState(0)
  const [data, setData] = useState<StudentListData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [archiveId, setArchiveId] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError('')
    listStudents({
      q: appliedQuery || undefined,
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
  }, [appliedQuery, grade, status, sort, direction, offset, refreshKey, t])

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
    setError('')
    try {
      await archiveStudent(archiveId)
      setNotice(t('students:archived'))
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
  const filtered = Boolean(appliedQuery || grade || status)

  return (
    <Stack spacing={3}>
      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        spacing={2}
        sx={{ justifyContent: 'space-between', alignItems: { sm: 'center' } }}
      >
        <Stack spacing={0.5}>
          <Typography variant="h2">{t('students:title')}</Typography>
          <Typography color="text.secondary">{t('students:description')}</Typography>
        </Stack>
        {hasPermission('students.create') ? (
          <Button component={Link} to="/app/students/new" variant="contained">
            {t('students:add')}
          </Button>
        ) : null}
      </Stack>
      {notice ? <Alert severity="success">{notice}</Alert> : null}
      {error ? <ErrorAlert message={error} /> : null}
      <Stack
        component="form"
        role="search"
        onSubmit={onSearch}
        direction={{ xs: 'column', md: 'row' }}
        spacing={1.5}
      >
        <TextField
          name="q"
          label={t('students:searchLabel')}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          fullWidth
          size="small"
        />
        <TextField
          select
          label={t('students:grade')}
          value={grade}
          onChange={(event) => {
            setOffset(0)
            setGrade(event.target.value)
          }}
          sx={{ minWidth: { xs: '100%', md: 160 } }}
          size="small"
        >
          <MenuItem value="">{t('students:allGrades')}</MenuItem>
          {GRADES.map((item) => (
            <MenuItem key={item} value={item}>
              {t('students:classOption', { grade: item })}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          select
          label={t('students:status')}
          value={status}
          onChange={(event) => {
            setOffset(0)
            setStatus(event.target.value)
          }}
          sx={{ minWidth: { xs: '100%', md: 180 } }}
          size="small"
        >
          <MenuItem value="">{t('students:statusCurrent')}</MenuItem>
          <MenuItem value="active">{t('students:statusActive')}</MenuItem>
          <MenuItem value="inactive">{t('students:statusInactive')}</MenuItem>
          <MenuItem value="archived">{t('students:statusArchived')}</MenuItem>
          <MenuItem value="all">{t('students:statusAll')}</MenuItem>
        </TextField>
        <Button type="submit" variant="outlined">
          {t('students:search')}
        </Button>
      </Stack>
      {loading && !data ? <LoadingScreen variant="section" /> : null}
      {!loading && error && !data ? (
        <Button variant="outlined" onClick={() => setRefreshKey((current) => current + 1)}>
          {t('students:retry')}
        </Button>
      ) : null}
      {data && data.items.length === 0 ? (
        <Typography>{filtered ? t('students:emptyFiltered') : t('students:empty')}</Typography>
      ) : null}
      {data && data.items.length > 0 ? (
        <TableContainer sx={{ overflowX: 'auto' }}>
          <Table aria-label={t('students:listLabel')} size="small">
            <TableHead>
              <TableRow>
                <TableCell>
                  <TableSortLabel
                    active={sort === 'code'}
                    direction={sort === 'code' ? direction : 'asc'}
                    onClick={() => changeSort('code')}
                  >
                    {t('students:studentId')}
                  </TableSortLabel>
                </TableCell>
                <TableCell>
                  <TableSortLabel
                    active={sort === 'name'}
                    direction={sort === 'name' ? direction : 'asc'}
                    onClick={() => changeSort('name')}
                  >
                    {t('students:fullName')}
                  </TableSortLabel>
                </TableCell>
                <TableCell>
                  <TableSortLabel
                    active={sort === 'grade'}
                    direction={sort === 'grade' ? direction : 'asc'}
                    onClick={() => changeSort('grade')}
                  >
                    {t('students:grade')}
                  </TableSortLabel>
                </TableCell>
                <TableCell sx={{ display: { xs: 'none', md: 'table-cell' } }}>{t('students:school')}</TableCell>
                <TableCell>{t('students:parents')}</TableCell>
                <TableCell sx={{ display: { xs: 'none', sm: 'table-cell' } }}>
                  <TableSortLabel
                    active={sort === 'enrollment'}
                    direction={sort === 'enrollment' ? direction : 'asc'}
                    onClick={() => changeSort('enrollment')}
                  >
                    {t('students:enrollment')}
                  </TableSortLabel>
                </TableCell>
                <TableCell>
                  <TableSortLabel
                    active={sort === 'status'}
                    direction={sort === 'status' ? direction : 'asc'}
                    onClick={() => changeSort('status')}
                  >
                    {t('students:status')}
                  </TableSortLabel>
                </TableCell>
                <TableCell>{t('students:actions')}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {data.items.map((student) => (
                <TableRow key={student.id} hover>
                  <TableCell>{student.student_code}</TableCell>
                  <TableCell>{student.full_name}</TableCell>
                  <TableCell>{student.grade ? t('students:classOption', { grade: student.grade }) : t('students:notProvided')}</TableCell>
                  <TableCell sx={{ display: { xs: 'none', md: 'table-cell' } }}>
                    {student.school_name || t('students:notProvided')}
                  </TableCell>
                  <TableCell>
                    {student.parents.length > 0
                      ? student.parents.map((parent) => parent.full_name).join(', ')
                      : t('students:notProvided')}
                  </TableCell>
                  <TableCell sx={{ display: { xs: 'none', sm: 'table-cell' } }}>
                    {student.enrollment_date ? formatDisplayDate(student.enrollment_date) : t('students:notProvided')}
                  </TableCell>
                  <TableCell>{t(`students:status${statusKey(student.status)}`)}</TableCell>
                  <TableCell>
                    <Stack direction={{ xs: 'column', lg: 'row' }} spacing={1}>
                      <Button component={Link} to={`/app/students/${student.id}`} size="small">
                        {t('students:view')}
                      </Button>
                      {hasPermission('students.update') ? (
                        <Button component={Link} to={`/app/students/${student.id}/edit`} size="small">
                          {t('students:edit')}
                        </Button>
                      ) : null}
                      {hasPermission('students.archive') && student.status !== 'archived' ? (
                        <Button size="small" color="error" onClick={() => setArchiveId(student.id)}>
                          {t('students:archive')}
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
            {t('students:previous')}
          </Button>
          <Typography>
            {t('students:page', { page, pages })}
          </Typography>
          <Button variant="outlined" disabled={offset + limit >= total} onClick={() => setOffset(offset + limit)}>
            {t('students:next')}
          </Button>
        </Stack>
      ) : null}
      <ConfirmDialog
        open={Boolean(archiveId)}
        title={t('students:confirmArchiveTitle')}
        description={t('students:confirmArchiveBody')}
        confirmLabel={t('students:archive')}
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
