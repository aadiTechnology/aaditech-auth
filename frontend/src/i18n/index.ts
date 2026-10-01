import i18n from 'i18next'
import LanguageDetector from 'i18next-browser-languagedetector'
import { initReactI18next } from 'react-i18next'

import enAccess from './locales/en/access.json'
import enAuth from './locales/en/auth.json'
import enCommon from './locales/en/common.json'
import enNavigation from './locales/en/navigation.json'
import enValidation from './locales/en/validation.json'
import hiAccess from './locales/hi/access.json'
import hiAuth from './locales/hi/auth.json'
import hiCommon from './locales/hi/common.json'
import hiNavigation from './locales/hi/navigation.json'
import hiValidation from './locales/hi/validation.json'
import mrAccess from './locales/mr/access.json'
import mrAuth from './locales/mr/auth.json'
import mrCommon from './locales/mr/common.json'
import mrNavigation from './locales/mr/navigation.json'
import mrValidation from './locales/mr/validation.json'

export const supportedLanguages = ['en', 'mr', 'hi'] as const
export type SupportedLanguage = (typeof supportedLanguages)[number]

void i18n.use(LanguageDetector).use(initReactI18next).init({
  resources: {
    en: {
      auth: enAuth,
      validation: enValidation,
      common: enCommon,
      navigation: enNavigation,
      access: enAccess,
    },
    mr: {
      auth: mrAuth,
      validation: mrValidation,
      common: mrCommon,
      navigation: mrNavigation,
      access: mrAccess,
    },
    hi: {
      auth: hiAuth,
      validation: hiValidation,
      common: hiCommon,
      navigation: hiNavigation,
      access: hiAccess,
    },
  },
  fallbackLng: 'en',
  supportedLngs: [...supportedLanguages],
  ns: ['common', 'auth', 'validation', 'navigation', 'access'],
  defaultNS: 'common',
  interpolation: { escapeValue: false },
  detection: {
    order: ['localStorage'],
    caches: ['localStorage'],
    lookupLocalStorage: 'preferred_language',
  },
})

function applyDocumentLanguage(language: string) {
  const base = language.split('-')[0]
  document.documentElement.lang = supportedLanguages.includes(base as SupportedLanguage) ? base : 'en'
}

applyDocumentLanguage(i18n.resolvedLanguage ?? 'en')
i18n.on('languageChanged', applyDocumentLanguage)

export default i18n
