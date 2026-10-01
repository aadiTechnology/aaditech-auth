import { Button, Stack, Typography } from '@mui/material'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

export function NotFoundPage() {
  const { t } = useTranslation('common')
  return (
    <Stack spacing={2} sx={{ p: 3 }}>
      <Typography variant="h1">{t('notFound')}</Typography>
      <Typography>{t('notFoundDescription')}</Typography>
      <Button component={Link} to="/" variant="contained" sx={{ alignSelf: 'flex-start' }}>
        {t('goHome')}
      </Button>
    </Stack>
  )
}
