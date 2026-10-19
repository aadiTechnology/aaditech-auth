import { Box, CircularProgress, Typography } from '@mui/material'
import { useTranslation } from 'react-i18next'

export function LoadingScreen({ variant = 'page' }: { variant?: 'page' | 'section' }) {
  const { t } = useTranslation('common')
  return (
    <Box
      role="status"
      aria-live="polite"
      sx={{
        minHeight: variant === 'page' ? '100vh' : 160,
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
