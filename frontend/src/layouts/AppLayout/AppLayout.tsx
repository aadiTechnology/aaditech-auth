import MenuIcon from '@mui/icons-material/Menu'
import {
  AppBar,
  Box,
  Button,
  Divider,
  Drawer,
  IconButton,
  Menu,
  MenuItem,
  Toolbar,
  Typography,
} from '@mui/material'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'

import { roleLabel } from '../../access/role-label'
import { LanguageSelect } from '../../components/common/LanguageSelect'
import { useAuth } from '../../store/auth-context'
import { AppSidebar } from './AppSidebar'
import { pageTitleKey } from './nav-items'
import { useDesktopLayout } from './useDesktopLayout'

const drawerWidth = 272

export function AppLayout() {
  const { t } = useTranslation(['auth', 'navigation', 'access'])
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const desktop = useDesktopLayout()
  const [mobileOpen, setMobileOpen] = useState(false)
  const [accountAnchor, setAccountAnchor] = useState<HTMLElement | null>(null)
  const roles = user?.roles.map((role) => roleLabel(role, t)).join(', ')
  const title = t(`navigation:${pageTitleKey(location.pathname)}`)

  async function onLogout() {
    setAccountAnchor(null)
    await logout()
    navigate('/login', { replace: true })
  }

  const sidebar = <AppSidebar showClose={!desktop} onNavigate={() => setMobileOpen(false)} />

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: 'background.default' }}>
      <Box sx={{ width: desktop ? drawerWidth : 0, flexShrink: 0 }}>
        {desktop ? (
          <Drawer
            variant="permanent"
            open
            sx={{
              width: drawerWidth,
              '& .MuiDrawer-paper': {
                width: drawerWidth,
                boxSizing: 'border-box',
                borderRight: '1px solid',
                borderColor: 'divider',
              },
            }}
          >
            {sidebar}
          </Drawer>
        ) : (
          <Drawer
            variant="temporary"
            open={mobileOpen}
            onClose={() => setMobileOpen(false)}
            transitionDuration={0}
            ModalProps={{ keepMounted: false }}
            sx={{ '& .MuiDrawer-paper': { width: drawerWidth, boxSizing: 'border-box' } }}
          >
            {sidebar}
          </Drawer>
        )}
      </Box>

      <Box component="main" sx={{ flexGrow: 1, minWidth: 0 }}>
        <AppBar
          position="fixed"
          elevation={0}
          sx={{
            width: desktop ? `calc(100% - ${drawerWidth}px)` : '100%',
            ml: desktop ? `${drawerWidth}px` : 0,
            borderBottom: '1px solid',
            borderColor: 'primary.dark',
          }}
        >
          <Toolbar sx={{ gap: 1 }}>
            {desktop ? null : (
              <IconButton
                color="inherit"
                edge="start"
                aria-label={t('navigation:openNavigation')}
                onClick={() => setMobileOpen(true)}
              >
                <MenuIcon />
              </IconButton>
            )}
            <Typography variant="h1" component="h1" noWrap sx={{ flexGrow: 1, fontSize: '1.25rem' }}>
              {title}
            </Typography>
            <Box
              sx={{
                width: { xs: 132, sm: 180 },
                bgcolor: 'background.paper',
                borderRadius: 1,
                px: 1,
                py: 0.5,
              }}
            >
              <LanguageSelect />
            </Box>
            <Button
              color="inherit"
              aria-haspopup="menu"
              aria-controls={accountAnchor ? 'account-menu' : undefined}
              aria-expanded={accountAnchor ? 'true' : undefined}
              aria-label={t('navigation:accountMenu')}
              onClick={(event) => setAccountAnchor(event.currentTarget)}
              sx={{ maxWidth: { xs: 120, sm: 200 } }}
            >
              <Typography noWrap>{user?.full_name}</Typography>
            </Button>
            <Menu
              id="account-menu"
              anchorEl={accountAnchor}
              open={Boolean(accountAnchor)}
              onClose={() => setAccountAnchor(null)}
              anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
              transformOrigin={{ vertical: 'top', horizontal: 'right' }}
            >
              <Box sx={{ px: 2, py: 1.5, maxWidth: 280 }}>
                <Typography variant="subtitle2">{user?.full_name}</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ wordBreak: 'break-word' }}>
                  {user?.email}
                </Typography>
                {roles ? (
                  <Typography variant="caption" color="text.secondary">
                    {roles}
                  </Typography>
                ) : null}
              </Box>
              <Divider />
              <MenuItem onClick={() => void onLogout()}>{t('auth:logout')}</MenuItem>
            </Menu>
          </Toolbar>
        </AppBar>
        <Toolbar />
        <Box sx={{ p: { xs: 2, sm: 3 } }}>
          <Outlet />
        </Box>
      </Box>
    </Box>
  )
}
