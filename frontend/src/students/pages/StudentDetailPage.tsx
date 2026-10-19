import { Alert, Button, MenuItem, Stack, TextField, Typography } from '@mui/material'
import { FormEvent, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'

import { usePermission } from '../../access/hooks/usePermission'
import { messageForError } from '../../auth/validation/errors'
import { ConfirmDialog } from '../../components/common/ConfirmDialog'
import { ErrorAlert } from '../../components/common/ErrorAlert'
import { LoadingScreen } from '../../components/common/LoadingScreen'
import { formatDisplayDate } from '../../roster/format'
import { ApiError } from '../../services/api/errors'
import { listBatches } from '../../batches/api'
import type { BatchListItem } from '../../batches/types'
import { listParents } from '../../parents/api'
import type { ParentListItem } from '../../parents/types'
import { archiveStudent, getStudent, linkParent, unlinkParent } from '../api'
import type { StudentDetail } from '../types'

export function StudentDetailPage() {
  const { studentId = '' } = useParams()
  const { t } = useTranslation(['students', 'common'])
  const { hasPermission } = usePermission()
  const navigate = useNavigate()
  const location = useLocation()
  const [notice, setNotice] = useState((location.state as { notice?: string } | null)?.notice ?? '')
  const [student, setStudent] = useState<StudentDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [missing, setMissing] = useState(false)
  const [error, setError] = useState('')
  const [archiveOpen, setArchiveOpen] = useState(false)
  const [unlinkId, setUnlinkId] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [parentQuery, setParentQuery] = useState('')
  const [parentResults, setParentResults] = useState<ParentListItem[]>([])
  const [parentId, setParentId] = useState('')
  const [relationship, setRelationship] = useState('')
  const canUpdate = hasPermission('students.update') && hasPermission('parents.update')
  const canReadParents = hasPermission('parents.read')
  const canReadBatches = hasPermission('batches.read')
  const [batchMembership, setBatchMembership] = useState<BatchListItem[]>([])
  const [batchNote, setBatchNote] = useState('')

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setMissing(false)
    setError('')
    getStudent(studentId)
      .then((result) => {
        if (!cancelled) {
          setStudent(result.data)
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
  }, [studentId, t])

  useEffect(() => {
    if (!canReadBatches) {
      return
    }
    let cancelled = false
    listBatches({ student_id: studentId, status: 'all', limit: 50 })
      .then((result) => {
        if (!cancelled) {
          setBatchMembership(result.data.items)
        }
      })
      .catch(() => {
        if (!cancelled) {
          setBatchNote(t('students:batchesUnavailable'))
        }
      })
    return () => {
      cancelled = true
    }
  }, [canReadBatches, studentId, t])

  async function confirmArchive() {
    setBusy(true)
    try {
      await archiveStudent(studentId)
      navigate('/app/students', { state: { notice: t('students:archived') } })
    } catch (requestError) {
      setError(messageForError(requestError, t))
      setArchiveOpen(false)
    } finally {
      setBusy(false)
    }
  }

  async function searchParents() {
    setBusy(true)
    setError('')
    try {
      const result = await listParents({ q: parentQuery.trim(), status: 'active', limit: 20 })
      const linked = new Set(student?.parents.map((parent) => parent.id))
      setParentResults(result.data.items.filter((parent) => !linked.has(parent.id)))
    } catch (requestError) {
      setError(messageForError(requestError, t))
    } finally {
      setBusy(false)
    }
  }

  async function onLink(event: FormEvent) {
    event.preventDefault()
    if (!parentId || busy) {
      return
    }
    setBusy(true)
    setError('')
    try {
      const result = await linkParent(studentId, { parent_id: parentId, relationship: relationship || null })
      setStudent(result.data)
      setNotice(t('students:parentLinked'))
      setParentId('')
      setRelationship('')
      setParentResults([])
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
      const result = await unlinkParent(studentId, unlinkId)
      setStudent(result.data)
      setNotice(t('students:parentUnlinked'))
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
  if (missing || !student) {
    return (
      <Stack spacing={2}>
        <Typography>{missing ? t('students:notFound') : error}</Typography>
        <Button component={Link} to="/app/students" variant="outlined">
          {t('students:back')}
        </Button>
      </Stack>
    )
  }

  return (
    <Stack spacing={3} sx={{ maxWidth: 800 }}>
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
        <Button component={Link} to="/app/students" variant="outlined">
          {t('students:back')}
        </Button>
        {hasPermission('students.update') ? (
          <Button component={Link} to={`/app/students/${student.id}/edit`} variant="contained">
            {t('students:edit')}
          </Button>
        ) : null}
        {hasPermission('students.archive') && student.status !== 'archived' ? (
          <Button color="error" variant="outlined" onClick={() => setArchiveOpen(true)}>
            {t('students:archive')}
          </Button>
        ) : null}
      </Stack>
      {notice ? <Alert severity="success">{notice}</Alert> : null}
      {error ? <ErrorAlert message={error} /> : null}
      <Stack spacing={0.5}>
        <Typography variant="h2">{student.full_name}</Typography>
        <Typography color="text.secondary">
          {t('students:studentId')}: {student.student_code}
        </Typography>
      </Stack>
      <DetailRow label={t('students:status')} value={t(`students:status${statusKey(student.status)}`)} />
      <DetailRow label={t('students:grade')} value={student.grade ? t('students:classOption', { grade: student.grade }) : null} />
      <DetailRow label={t('students:school')} value={student.school_name} />
      <DetailRow label={t('students:dateOfBirth')} value={formatDisplayDate(student.date_of_birth)} />
      <DetailRow label={t('students:enrollment')} value={formatDisplayDate(student.enrollment_date)} />
      <DetailRow label={t('students:address')} value={student.address} />
      <DetailRow label={t('students:notes')} value={student.notes} />
      {canReadBatches ? (
        <Stack spacing={1}>
          <Typography variant="h2">{t('students:batchMembership')}</Typography>
          {batchNote ? <Typography color="text.secondary">{batchNote}</Typography> : null}
          {batchMembership.length === 0 && !batchNote ? <Typography>{t('students:noBatches')}</Typography> : null}
          {batchMembership.map((batch) => (
            <Button key={batch.id} component={Link} to={`/app/batches/${batch.id}`} sx={{ alignSelf: 'flex-start' }}>
              {batch.name} ({batch.batch_code})
            </Button>
          ))}
        </Stack>
      ) : null}
      <Typography variant="h2">{t('students:linkedParents')}</Typography>
      {student.parents.length === 0 ? <Typography>{t('students:noParents')}</Typography> : null}
      {student.parents.map((parent) => (
        <Stack key={parent.id} spacing={0.5} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2, p: 2 }}>
          {canReadParents ? (
            <Button component={Link} to={`/app/parents/${parent.id}`} sx={{ alignSelf: 'flex-start', px: 0 }}>
              {parent.full_name}
            </Button>
          ) : (
            <Typography fontWeight={700}>{parent.full_name}</Typography>
          )}
          <Typography>
            {t('students:relationship')}: {relationshipLabel(parent.relationship, t)}
          </Typography>
          <Typography>
            {t('students:phone')}: {parent.phone || t('students:notProvided')}
          </Typography>
          <Typography>
            {t('students:email')}: {parent.email || t('students:notProvided')}
          </Typography>
          {canUpdate ? (
            <Button color="error" sx={{ alignSelf: 'flex-start' }} onClick={() => setUnlinkId(parent.id)}>
              {t('students:unlink')}
            </Button>
          ) : null}
        </Stack>
      ))}
      {canUpdate && canReadParents ? (
        <Stack component="form" spacing={1.5} onSubmit={onLink}>
          <Typography fontWeight={700}>{t('students:linkParent')}</Typography>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} component="div">
            <TextField
              label={t('students:parentSearch')}
              value={parentQuery}
              onChange={(event) => setParentQuery(event.target.value)}
              fullWidth
              size="small"
            />
            <Button type="button" variant="outlined" onClick={() => void searchParents()} disabled={busy}>
              {t('students:search')}
            </Button>
          </Stack>
          <TextField
            select
            label={t('students:chooseParent')}
            value={parentId}
            onChange={(event) => setParentId(event.target.value)}
            fullWidth
          >
            <MenuItem value="">{t('students:chooseParent')}</MenuItem>
            {parentResults.map((parent) => (
              <MenuItem key={parent.id} value={parent.id}>
                {parent.full_name}
              </MenuItem>
            ))}
          </TextField>
          <TextField select label={t('students:relationship')} value={relationship} onChange={(event) => setRelationship(event.target.value)} fullWidth>
            <MenuItem value="">{t('students:relationshipNone')}</MenuItem>
            <MenuItem value="mother">{t('students:relationshipMother')}</MenuItem>
            <MenuItem value="father">{t('students:relationshipFather')}</MenuItem>
            <MenuItem value="guardian">{t('students:relationshipGuardian')}</MenuItem>
            <MenuItem value="other">{t('students:relationshipOther')}</MenuItem>
          </TextField>
          <Button type="submit" variant="contained" disabled={!parentId || busy} sx={{ alignSelf: 'flex-start' }}>
            {t('students:linkParent')}
          </Button>
        </Stack>
      ) : null}
      <ConfirmDialog
        open={archiveOpen}
        title={t('students:confirmArchiveTitle')}
        description={t('students:confirmArchiveBody')}
        confirmLabel={t('students:archive')}
        busy={busy}
        onClose={() => setArchiveOpen(false)}
        onConfirm={() => void confirmArchive()}
      />
      <ConfirmDialog
        open={Boolean(unlinkId)}
        title={t('students:confirmUnlinkTitle')}
        description={t('students:confirmUnlinkBody')}
        confirmLabel={t('students:unlink')}
        busy={busy}
        onClose={() => setUnlinkId(null)}
        onConfirm={() => void confirmUnlink()}
      />
    </Stack>
  )
}

function DetailRow({ label, value }: { label: string; value: string | null | undefined }) {
  const { t } = useTranslation('students')
  return (
    <Typography>
      {label}: {value?.trim() ? value : t('notProvided')}
    </Typography>
  )
}

function relationshipLabel(value: string | null, t: (key: string) => string) {
  if (value === 'mother') return t('students:relationshipMother')
  if (value === 'father') return t('students:relationshipFather')
  if (value === 'guardian') return t('students:relationshipGuardian')
  if (value === 'other') return t('students:relationshipOther')
  return t('students:relationshipNone')
}

function statusKey(status: string) {
  return `${status.charAt(0).toUpperCase()}${status.slice(1)}`
}
