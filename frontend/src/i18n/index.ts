import { createI18n } from 'vue-i18n'

import { messages } from './messages'

export type AppLocale = keyof typeof messages
const savedLocale = window.localStorage.getItem('academicnexus.locale') as AppLocale | null
export const defaultLocale: AppLocale = savedLocale === 'en-US' ? 'en-US' : 'zh-CN'

export const i18n = createI18n({
  legacy: false,
  locale: defaultLocale,
  fallbackLocale: 'zh-CN',
  messages,
})

export function toggleLocale(): AppLocale {
  const nextLocale: AppLocale = i18n.global.locale.value === 'zh-CN' ? 'en-US' : 'zh-CN'
  i18n.global.locale.value = nextLocale
  window.localStorage.setItem('academicnexus.locale', nextLocale)
  document.documentElement.lang = nextLocale
  return nextLocale
}
