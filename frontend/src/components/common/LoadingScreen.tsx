import { Box, CircularProgress, Typography } from '@mui/material'
import { useTranslation } from 'react-i18next'

export function LoadingScreen() {
  const { t } = useTranslation('common')
  return (
    <Box
      role="status"
      aria-live="polite"
      sx={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 2,
      }}
    >
      <CircularProgress />
      <Typography>{t('loading')}</Typography>
    </Box>
  )
}
