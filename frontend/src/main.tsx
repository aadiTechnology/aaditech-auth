import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import { App } from './app/App'
import './i18n'
import i18n from './i18n'

document.title = i18n.t('auth:appName')
i18n.on('languageChanged', () => {
  document.title = i18n.t('auth:appName')
})

const root = document.getElementById('root')
if (!root) {
  throw new Error('Root element was not found')
}

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
