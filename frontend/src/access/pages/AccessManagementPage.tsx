import {
  Alert,
  Button,
  Card,
  CardContent,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from '@mui/material'
import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import type { AccessUser, RolePublic } from '../../auth/types'
import { roleLabel } from '../role-label'
import { ErrorAlert } from '../../components/common/ErrorAlert'
import { LoadingScreen } from '../../components/common/LoadingScreen'
import { ApiError } from '../../services/api/errors'
import { api } from '../../services/api/client'
import { messageForError } from '../../auth/validation/errors'
import { useAuth } from '../../store/auth-context'

export function AccessManagementPage() {
  const { t } = useTranslation(['access', 'common'])
  const { user } = useAuth()
  const [users, setUsers] = useState<AccessUser[]>([])
  const [roles, setRoles] = useState<RolePublic[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busyId, setBusyId] = useState<string | null>(null)
  const [roleTarget, setRoleTarget] = useState<AccessUser | null>(null)
  const [selectedRole, setSelectedRole] = useState('STUDENT')
  const [statusTarget, setStatusTarget] = useState<AccessUser | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [userResult, roleResult] = await Promise.all([
        api.get<{ items: AccessUser[]; total: number }>('/api/v1/users'),
        api.get<RolePublic[]>('/api/v1/roles'),
      ])
      setUsers(userResult.data.items)
      setRoles(roleResult.data)
    } catch (requestError) {
      setError(messageForError(requestError, t))
    } finally {
      setLoading(false)
    }
  }, [t])

  useEffect(() => {
    void load()
  }, [load])

  async function saveRole() {
    if (!roleTarget) return
    setBusyId(roleTarget.id)
    setNotice('')
    try {
      await api.patch(`/api/v1/users/${roleTarget.id}/role`, { role: selectedRole })
      setNotice(t('access:roleUpdated'))
      setRoleTarget(null)
      await load()
    } catch (requestError) {
      setError(requestError instanceof ApiError ? messageForError(requestError, t) : t('common:unexpectedError'))
    } finally {
      setBusyId(null)
    }
  }

  async function saveStatus() {
    if (!statusTarget) return
    setBusyId(statusTarget.id)
    setNotice('')
    try {
      await api.patch(`/api/v1/users/${statusTarget.id}/status`, { is_active: !statusTarget.is_active })
      setNotice(statusTarget.is_active ? t('access:userDeactivated') : t('access:userActivated'))
      setStatusTarget(null)
      await load()
    } catch (requestError) {
      setError(messageForError(requestError, t))
    } finally {
      setBusyId(null)
    }
  }

  if (loading && users.length === 0) {
    return <LoadingScreen />
  }

  return (
    <Stack spacing={3}>
      <Typography variant="h1">{t('access:title')}</Typography>
      <Typography color="text.secondary">{t('access:description')}</Typography>
      {notice ? <Alert severity="success">{notice}</Alert> : null}
      {error ? <ErrorAlert message={error} /> : null}
      {users.length === 0 ? <Typography>{t('access:noUsers')}</Typography> : null}
      <Stack spacing={2}>
        {users.map((account) => {
          const isSelf = account.id === user?.id
          return (
            <Card key={account.id} variant="outlined">
              <CardContent>
                <Stack spacing={1}>
                  <Typography fontWeight={700}>{account.full_name}</Typography>
                  <Typography>
                    {t('access:email')}: {account.email}
                  </Typography>
                  <Typography>
                    {t('access:role')}: {account.roles.map((role) => roleLabel(role, t)).join(', ')}
                  </Typography>
                  <Typography>
                    {t('access:status')}: {account.is_active ? t('access:active') : t('access:inactive')}
                  </Typography>
                  {isSelf ? <Typography>{t('access:cannotChangeSelf')}</Typography> : null}
                  <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
                    <Button
                      variant="outlined"
                      disabled={isSelf || busyId === account.id}
                      onClick={() => {
                        setSelectedRole(account.roles[0] ?? 'STUDENT')
                        setRoleTarget(account)
                      }}
                    >
                      {t('access:changeRole')}
                    </Button>
                    <Button
                      variant="outlined"
                      color={account.is_active ? 'error' : 'primary'}
                      disabled={isSelf || busyId === account.id}
                      onClick={() => setStatusTarget(account)}
                    >
                      {account.is_active ? t('access:deactivate') : t('access:activate')}
                    </Button>
                  </Stack>
                </Stack>
              </CardContent>
            </Card>
          )
        })}
      </Stack>
      <Stack spacing={1}>
        <Typography variant="h2" sx={{ fontSize: '1.25rem' }}>
          {t('access:rolesAndPermissions')}
        </Typography>
        {roles.map((role) => (
          <Typography key={role.id}>
            {roleLabel(role.name, t)}:{' '}
            {role.permissions
              .map((permission) => t(`access:permission_${permission.key.replaceAll('.', '_')}`, { defaultValue: permission.description }))
              .join(', ')}
          </Typography>
        ))}
      </Stack>
      <Dialog open={Boolean(roleTarget)} onClose={() => setRoleTarget(null)} aria-labelledby="change-role-title">
        <DialogTitle id="change-role-title">{t('access:confirmRole')}</DialogTitle>
        <DialogContent>
          <TextField
            select
            fullWidth
            label={t('access:selectRole')}
            value={selectedRole}
            onChange={(event) => setSelectedRole(event.target.value)}
            sx={{ mt: 1, minWidth: { xs: '100%', sm: 280 } }}
          >
            {roles.map((role) => (
              <MenuItem key={role.id} value={role.name}>
                {roleLabel(role.name, t)}
              </MenuItem>
            ))}
          </TextField>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRoleTarget(null)}>{t('common:cancel')}</Button>
          <Button variant="contained" onClick={() => void saveRole()}>
            {t('common:save')}
          </Button>
        </DialogActions>
      </Dialog>
      <Dialog open={Boolean(statusTarget)} onClose={() => setStatusTarget(null)} aria-labelledby="status-title">
        <DialogTitle id="status-title">
          {statusTarget?.is_active ? t('access:confirmDeactivate') : t('access:confirmActivate')}
        </DialogTitle>
        <DialogActions>
          <Button onClick={() => setStatusTarget(null)}>{t('common:cancel')}</Button>
          <Button variant="contained" onClick={() => void saveStatus()}>
            {t('common:save')}
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  )
}
