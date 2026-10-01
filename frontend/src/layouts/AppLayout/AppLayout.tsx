import { AppBar, Box, Button, Container, Stack, Toolbar, Typography } from '@mui/material'
import { useTranslation } from 'react-i18next'
import { Link, Outlet, useNavigate } from 'react-router-dom'

import { usePermission } from '../../access/hooks/usePermission'
import { LanguageSelect } from '../../components/common/LanguageSelect'
import { useAuth } from '../../store/auth-context'

export function AppLayout() {
  const { t } = useTranslation(['auth', 'navigation', 'common'])
  const { user, logout } = useAuth()
  const { hasPermission } = usePermission()
  const navigate = useNavigate()

  async function onLogout() {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
      <AppBar position="static">
        <Toolbar sx={{ gap: 2, flexWrap: 'wrap', py: 1 }}>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            {t('auth:appName')}
          </Typography>
          <Box sx={{ minWidth: { xs: '100%', sm: 220 }, bgcolor: 'background.paper', borderRadius: 1, px: 1, py: 0.5 }}>
            <LanguageSelect />
          </Box>
          <Button color="inherit" onClick={() => void onLogout()}>
            {t('auth:logout')}
          </Button>
        </Toolbar>
      </AppBar>
      <Container sx={{ py: { xs: 2, sm: 4 } }}>
        <Stack component="nav" aria-label={t('navigation:mainNavigation')} direction="row" spacing={2} sx={{ mb: 3 }}>
          <Button component={Link} to="/app">
            {t('navigation:home')}
          </Button>
          {hasPermission('users.read') ? (
            <Button component={Link} to="/app/admin/access">
              {t('navigation:accessManagement')}
            </Button>
          ) : null}
        </Stack>
        <Outlet context={{ user }} />
      </Container>
    </Box>
  )
}
