import { Box, Paper, Stack, Typography } from '@mui/material'
import { useTranslation } from 'react-i18next'
import { Outlet } from 'react-router-dom'

import { LanguageSelect } from '../../components/common/LanguageSelect'

export function AuthLayout() {
  const { t } = useTranslation('auth')

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        px: { xs: 2, sm: 3 },
        py: 4,
      }}
    >
      <Stack spacing={2} sx={{ width: '100%', maxWidth: 440 }}>
        <Typography variant="h6" component="p" sx={{ fontWeight: 700, textAlign: 'center' }}>
          {t('appName')}
        </Typography>
        <LanguageSelect />
        <Paper data-testid="auth-card" sx={{ p: { xs: 2.5, sm: 4 }, width: '100%' }}>
          <Outlet />
        </Paper>
      </Stack>
    </Box>
  )
}
