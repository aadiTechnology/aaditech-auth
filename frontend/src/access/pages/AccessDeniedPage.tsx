import { Button, Stack, Typography } from '@mui/material'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

export function AccessDeniedPage() {
  const { t } = useTranslation('access')
  return (
    <Stack spacing={2} role="alert">
      <Typography variant="h1">{t('deniedTitle')}</Typography>
      <Typography>{t('deniedMessage')}</Typography>
      <Button component={Link} to="/app" variant="contained" sx={{ alignSelf: 'flex-start' }}>
        {t('backToApp')}
      </Button>
    </Stack>
  )
}
