import { Alert, Button, MenuItem, Stack, TextField, Typography } from '@mui/material'
import { FormEvent, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'

import { usePermission } from '../../access/hooks/usePermission'
import { messageForError } from '../../auth/validation/errors'
import { ConfirmDialog } from '../../components/common/ConfirmDialog'
import { ErrorAlert } from '../../components/common/ErrorAlert'
import { LoadingScreen } from '../../components/common/LoadingScreen'
import { ApiError } from '../../services/api/errors'
import { listStudents } from '../../students/api'
import type { StudentListItem } from '../../students/types'
import { archiveParent, getParent, linkStudent, unlinkStudent } from '../api'
import type { ParentDetail } from '../types'

export function ParentDetailPage() {
  const { parentId = '' } = useParams()
  const { t } = useTranslation(['parents', 'students', 'common'])
  const { hasPermission } = usePermission()
  const navigate = useNavigate()
  const location = useLocation()
  const [notice, setNotice] = useState((location.state as { notice?: string } | null)?.notice ?? '')
  const [parent, setParent] = useState<ParentDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [missing, setMissing] = useState(false)
  const [error, setError] = useState('')
  const [archiveOpen, setArchiveOpen] = useState(false)
  const [unlinkId, setUnlinkId] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [studentQuery, setStudentQuery] = useState('')
  const [studentResults, setStudentResults] = useState<StudentListItem[]>([])
  const [studentId, setStudentId] = useState('')
  const [relationship, setRelationship] = useState('')
  const canUpdate = hasPermission('parents.update') && hasPermission('students.update')
  const canReadStudents = hasPermission('students.read')

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    getParent(parentId)
      .then((result) => {
        if (!cancelled) {
          setParent(result.data)
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
  }, [parentId, t])

  async function confirmArchive() {
    setBusy(true)
    try {
      await archiveParent(parentId)
      navigate('/app/parents', { state: { notice: t('parents:archived') } })
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
      const result = await listStudents({ q: studentQuery.trim(), status: 'all', limit: 20 })
      const linked = new Set(parent?.students.map((student) => student.id))
      setStudentResults(result.data.items.filter((student) => !linked.has(student.id) && student.status !== 'archived'))
    } catch (requestError) {
      setError(messageForError(requestError, t))
    } finally {
      setBusy(false)
    }
  }

  async function onLink(event: FormEvent) {
    event.preventDefault()
    if (!studentId || busy) {
      return
    }
    setBusy(true)
    setError('')
    try {
      const result = await linkStudent(parentId, { student_id: studentId, relationship: relationship || null })
      setParent(result.data)
      setNotice(t('parents:studentLinked'))
      setStudentId('')
      setRelationship('')
      setStudentResults([])
    } catch (requestError) {
      setError(messageForError(requestError, t))
    } finally {
      setBusy(false)
    }
  }

  async function confirmUnlink() {
    if (!unlinkId) {
      return
    }
    setBusy(true)
    try {
      const result = await unlinkStudent(parentId, unlinkId)
      setParent(result.data)
      setNotice(t('parents:studentUnlinked'))
      setUnlinkId(null)
    } catch (requestError) {
      setError(messageForError(requestError, t))
      setUnlinkId(null)
    } finally {
      setBusy(false)
    }
  }

  if (loading) {
    return <LoadingScreen variant="section" />
  }
  if (missing || !parent) {
    return (
      <Stack spacing={2}>
        <Typography>{missing ? t('parents:notFound') : error}</Typography>
        <Button component={Link} to="/app/parents" variant="outlined">
          {t('parents:back')}
        </Button>
      </Stack>
    )
  }

  return (
    <Stack spacing={3} sx={{ maxWidth: 800 }}>
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
        <Button component={Link} to="/app/parents" variant="outlined">
          {t('parents:back')}
        </Button>
        {hasPermission('parents.update') ? (
          <Button component={Link} to={`/app/parents/${parent.id}/edit`} variant="contained">
            {t('parents:edit')}
          </Button>
        ) : null}
        {hasPermission('parents.archive') && parent.status !== 'archived' ? (
          <Button color="error" variant="outlined" onClick={() => setArchiveOpen(true)}>
            {t('parents:archive')}
          </Button>
        ) : null}
      </Stack>
      {notice ? <Alert severity="success">{notice}</Alert> : null}
      {error ? <ErrorAlert message={error} /> : null}
      <Typography variant="h2">{parent.full_name}</Typography>
      <Typography>
        {t('parents:phone')}: {parent.phone || t('parents:notProvided')}
      </Typography>
      <Typography>
        {t('parents:email')}: {parent.email || t('parents:notProvided')}
      </Typography>
      <Typography>
        {t('parents:address')}: {parent.address || t('parents:notProvided')}
      </Typography>
      <Typography>
        {t('parents:notes')}: {parent.notes || t('parents:notProvided')}
      </Typography>
      <Typography>
        {t('parents:status')}: {t(`parents:status${statusKey(parent.status)}`)}
      </Typography>
      <Typography variant="h2">{t('parents:linkedStudents')}</Typography>
      {parent.students.length === 0 ? <Typography>{t('parents:noStudents')}</Typography> : null}
      {parent.students.map((student) => (
        <Stack key={student.id} spacing={0.5} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2, p: 2 }}>
          {canReadStudents ? (
            <Button component={Link} to={`/app/students/${student.id}`} sx={{ alignSelf: 'flex-start', px: 0 }}>
              {student.full_name}
            </Button>
          ) : (
            <Typography fontWeight={700}>{student.full_name}</Typography>
          )}
          <Typography>
            {t('parents:studentId')}: {student.student_code}
          </Typography>
          <Typography>
            {t('parents:relationship')}: {relationshipLabel(student.relationship, t)}
          </Typography>
          {canUpdate ? (
            <Button color="error" sx={{ alignSelf: 'flex-start' }} onClick={() => setUnlinkId(student.id)}>
              {t('parents:unlink')}
            </Button>
          ) : null}
        </Stack>
      ))}
      {canUpdate && canReadStudents && parent.status !== 'archived' ? (
        <Stack component="form" spacing={1.5} onSubmit={onLink}>
          <Typography fontWeight={700}>{t('parents:linkStudent')}</Typography>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
            <TextField
              label={t('parents:studentSearch')}
              value={studentQuery}
              onChange={(event) => setStudentQuery(event.target.value)}
              fullWidth
              size="small"
            />
            <Button type="button" variant="outlined" onClick={() => void searchStudents()} disabled={busy}>
              {t('parents:search')}
            </Button>
          </Stack>
          <TextField select label={t('parents:chooseStudent')} value={studentId} onChange={(event) => setStudentId(event.target.value)} fullWidth>
            <MenuItem value="">{t('parents:chooseStudent')}</MenuItem>
            {studentResults.map((student) => (
              <MenuItem key={student.id} value={student.id}>
                {student.full_name} ({student.student_code})
              </MenuItem>
            ))}
          </TextField>
          <TextField select label={t('parents:relationship')} value={relationship} onChange={(event) => setRelationship(event.target.value)} fullWidth>
            <MenuItem value="">{t('parents:relationshipNone')}</MenuItem>
            <MenuItem value="mother">{t('parents:relationshipMother')}</MenuItem>
            <MenuItem value="father">{t('parents:relationshipFather')}</MenuItem>
            <MenuItem value="guardian">{t('parents:relationshipGuardian')}</MenuItem>
            <MenuItem value="other">{t('parents:relationshipOther')}</MenuItem>
          </TextField>
          <Button type="submit" variant="contained" disabled={!studentId || busy} sx={{ alignSelf: 'flex-start' }}>
            {t('parents:linkStudent')}
          </Button>
        </Stack>
      ) : null}
      <ConfirmDialog
        open={archiveOpen}
        title={t('parents:confirmArchiveTitle')}
        description={t('parents:confirmArchiveBody')}
        confirmLabel={t('parents:archive')}
        busy={busy}
        onClose={() => setArchiveOpen(false)}
        onConfirm={() => void confirmArchive()}
      />
      <ConfirmDialog
        open={Boolean(unlinkId)}
        title={t('parents:confirmUnlinkTitle')}
        description={t('parents:confirmUnlinkBody')}
        confirmLabel={t('parents:unlink')}
        busy={busy}
        onClose={() => setUnlinkId(null)}
        onConfirm={() => void confirmUnlink()}
      />
    </Stack>
  )
}

function relationshipLabel(value: string | null, t: (key: string) => string) {
  if (value === 'mother') return t('parents:relationshipMother')
  if (value === 'father') return t('parents:relationshipFather')
  if (value === 'guardian') return t('parents:relationshipGuardian')
  if (value === 'other') return t('parents:relationshipOther')
  return t('parents:relationshipNone')
}

function statusKey(status: string) {
  return `${status.charAt(0).toUpperCase()}${status.slice(1)}`
}
