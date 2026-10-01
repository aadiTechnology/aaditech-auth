import { TextField } from '@mui/material'
import { useTranslation } from 'react-i18next'

import i18n, { supportedLanguages, type SupportedLanguage } from '../../i18n'

const labels: Record<SupportedLanguage, string> = {
  en: 'english',
  mr: 'marathi',
  hi: 'hindi',
}

export function LanguageSelect() {
  const { t } = useTranslation('common')
  const current = (i18n.resolvedLanguage ?? 'en').split('-')[0]
  const value = supportedLanguages.includes(current as SupportedLanguage)
    ? (current as SupportedLanguage)
    : 'en'

  return (
    <TextField
      select
      fullWidth
      label={t('language')}
      value={value}
      onChange={(event) => {
        void i18n.changeLanguage(event.target.value)
      }}
      slotProps={{
        select: { native: true },
      }}
    >
      {supportedLanguages.map((language) => (
        <option key={language} value={language}>
          {t(labels[language])}
        </option>
      ))}
    </TextField>
  )
}
