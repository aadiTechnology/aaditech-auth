import { Box, Paper, Stack } from '@mui/material'
import { Outlet } from 'react-router-dom'

import { LanguageSelect } from '../../components/common/LanguageSelect'

export function AuthLayout() {
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
        <LanguageSelect />
        <Paper data-testid="auth-card" sx={{ p: { xs: 2.5, sm: 4 }, width: '100%' }}>
          <Outlet />
        </Paper>
      </Stack>
    </Box>
  )
}
