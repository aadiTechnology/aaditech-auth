import { Stack, Typography } from '@mui/material'
import { useTranslation } from 'react-i18next'

import { roleLabel } from '../role-label'
import { useAuth } from '../../store/auth-context'

export function HomePage() {
  const { t } = useTranslation(['auth', 'access'])
  const { user } = useAuth()
  const roles = user?.roles.map((role) => roleLabel(role, t)).join(', ')

  return (
    <Stack spacing={1}>
      <Typography variant="h1">{t('auth:welcome')}</Typography>
      <Typography>{t('auth:signedInAs', { name: user?.full_name ?? '' })}</Typography>
      <Typography>
        {t('auth:currentRole')}: {roles}
      </Typography>
    </Stack>
  )
}
