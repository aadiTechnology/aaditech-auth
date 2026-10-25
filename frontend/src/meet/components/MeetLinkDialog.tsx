import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Stack,
  TextField,
  Typography,
} from '@mui/material'
import { useEffect, useId, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { messageForError } from '../../auth/validation/errors'
import { ErrorAlert } from '../../components/common/ErrorAlert'
import { LoadingScreen } from '../../components/common/LoadingScreen'
import { getMeeting, updateMeeting } from '../api'
import { normalizeMeetUrl } from '../url'

export function MeetLinkDialog({
  open,
  classId,
  onClose,
  onSaved,
}: {
  open: boolean
  classId: string | null
  onClose: () => void
  onSaved: (message: string) => void
}) {
  const { t } = useTranslation(['meet', 'common'])
  const titleId = useId()
  const [url, setUrl] = useState('')
  const [version, setVersion] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [fieldError, setFieldError] = useState('')

  useEffect(() => {
    if (!open || !classId) {
      return
    }
    let cancelled = false
    setLoading(true)
    setError('')
    setFieldError('')
    getMeeting(classId)
      .then((result) => {
        if (!cancelled) {
          setUrl(result.data.meet_url ?? '')
          setVersion(result.data.version)
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
  }, [open, classId, t])

  async function save(next: string | null) {
    if (!classId || version == null) {
      return
    }
    if (next) {
      try {
        normalizeMeetUrl(next)
      } catch {
        setFieldError(t('meet:invalidUrl'))
        return
      }
    }
    setSaving(true)
    setError('')
    setFieldError('')
    try {
      await updateMeeting(classId, { version, meet_url: next })
      onSaved(next ? t('meet:saved') : t('meet:cleared'))
      onClose()
    } catch (requestError: unknown) {
      setError(messageForError(requestError, t))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onClose={saving ? undefined : onClose} aria-labelledby={titleId} fullWidth maxWidth="sm">
      <DialogTitle id={titleId}>{t('meet:dialogTitle')}</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ pt: 1 }}>
          <Typography color="text.secondary">{t('meet:urlHelp')}</Typography>
          <Typography variant="body2" color="text.secondary">
            {t('meet:expiryNote')}
          </Typography>
          {loading ? <LoadingScreen variant="section" /> : null}
          {error ? <ErrorAlert message={error} /> : null}
          <TextField
            label={t('meet:urlLabel')}
            value={url}
            onChange={(event) => setUrl(event.target.value)}
            error={Boolean(fieldError)}
            helperText={fieldError || ' '}
            disabled={loading || saving || version == null}
            fullWidth
            slotProps={{ htmlInput: { maxLength: 300 } }}
          />
        </Stack>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2, flexWrap: 'wrap', gap: 1 }}>
        <Button onClick={onClose} disabled={saving}>
          {t('common:cancel')}
        </Button>
        <Button onClick={() => void save(null)} disabled={saving || loading || version == null || !url.trim()} color="inherit">
          {t('meet:clear')}
        </Button>
        <Button variant="contained" onClick={() => void save(url.trim())} disabled={saving || loading || version == null}>
          {saving ? t('meet:saving') : t('meet:save')}
        </Button>
      </DialogActions>
    </Dialog>
  )
}
