import CloseIcon from '@mui/icons-material/Close'
import { Box, Divider, IconButton, List, ListItem, ListItemButton, ListItemIcon, ListItemText, Toolbar, Typography } from '@mui/material'
import { useTranslation } from 'react-i18next'
import { Link, useLocation } from 'react-router-dom'

import { usePermission } from '../../access/hooks/usePermission'
import { adminNavItems, isNavItemSelected, primaryNavItems, type AppNavItem } from './nav-items'

export function AppSidebar({ onNavigate, showClose = false }: { onNavigate: () => void; showClose?: boolean }) {
  const { t } = useTranslation(['navigation', 'auth'])
  const { hasPermission } = usePermission()
  const visiblePrimaryItems = primaryNavItems.filter((item) => !item.permission || hasPermission(item.permission))
  const visibleAdminItems = adminNavItems.filter((item) => !item.permission || hasPermission(item.permission))

  return (
    <Box
      component="nav"
      aria-label={t('navigation:mainNavigation')}
      sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}
    >
      <Toolbar sx={{ gap: 1 }}>
        <Typography variant="h6" component="div" sx={{ flexGrow: 1, fontWeight: 700 }}>
          {t('auth:appName')}
        </Typography>
        {showClose ? (
          <IconButton aria-label={t('navigation:closeNavigation')} onClick={onNavigate} edge="end">
            <CloseIcon />
          </IconButton>
        ) : null}
      </Toolbar>
      <Divider />
      <List sx={{ px: 1, py: 1 }}>
        {visiblePrimaryItems.map((item) => (
          <NavEntry key={item.id} item={item} onNavigate={onNavigate} />
        ))}
      </List>
      {visibleAdminItems.length > 0 ? (
        <>
          <Divider />
          <List sx={{ px: 1, py: 1 }}>
            {visibleAdminItems.map((item) => (
              <NavEntry key={item.id} item={item} onNavigate={onNavigate} />
            ))}
          </List>
        </>
      ) : null}
    </Box>
  )
}

function NavEntry({ item, onNavigate }: { item: AppNavItem; onNavigate: () => void }) {
  const { t } = useTranslation('navigation')
  const location = useLocation()
  const Icon = item.icon
  const selected = isNavItemSelected(location.pathname, item)

  if (item.comingSoon || !item.to) {
    return (
      <ListItem disablePadding sx={{ mb: 0.5 }}>
        <ListItemButton disabled>
          <ListItemIcon>
            <Icon />
          </ListItemIcon>
          <ListItemText primary={t(item.labelKey)} secondary={t('comingSoon')} />
        </ListItemButton>
      </ListItem>
    )
  }

  return (
    <ListItem disablePadding sx={{ mb: 0.5 }}>
      <ListItemButton
        component={Link}
        to={item.to}
        selected={selected}
        aria-current={selected ? 'page' : undefined}
        onClick={onNavigate}
      >
        <ListItemIcon>
          <Icon />
        </ListItemIcon>
        <ListItemText primary={t(item.labelKey)} />
      </ListItemButton>
    </ListItem>
  )
}
