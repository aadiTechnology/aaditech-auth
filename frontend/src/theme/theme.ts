import { createTheme } from '@mui/material/styles'

const focusRing = {
  '&:focus-visible': {
    outline: '3px solid #0D47A1',
    outlineOffset: '2px',
  },
}

export const theme = createTheme({
  palette: {
    mode: 'light',
    primary: { main: '#0D47A1' },
    secondary: { main: '#00695C' },
    background: { default: '#F4F7FB', paper: '#FFFFFF' },
    text: { primary: '#1C1B1F', secondary: '#3F4946' },
    error: { main: '#B3261E' },
  },
  typography: {
    fontFamily: '"Segoe UI", "Noto Sans", "Noto Sans Devanagari", sans-serif',
    h1: { fontSize: '1.75rem', fontWeight: 700 },
  },
  shape: { borderRadius: 12 },
  components: {
    MuiButton: {
      styleOverrides: {
        root: { textTransform: 'none', fontWeight: 600, minHeight: 44, ...focusRing },
      },
    },
    MuiIconButton: { styleOverrides: { root: focusRing } },
    MuiLink: { styleOverrides: { root: focusRing } },
    MuiCssBaseline: {
      styleOverrides: {
        body: { margin: 0 },
      },
    },
  },
})
