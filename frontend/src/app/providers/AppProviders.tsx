import { CssBaseline, ThemeProvider } from '@mui/material'
import { type ReactNode } from 'react'
import { BrowserRouter } from 'react-router-dom'

import { AuthProvider } from '../../store/auth-context'
import { theme } from '../../theme/theme'

export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <AuthProvider>
        <BrowserRouter>{children}</BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  )
}
