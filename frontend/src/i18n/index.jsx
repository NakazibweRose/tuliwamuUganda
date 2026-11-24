import { createContext, useCallback, useContext, useMemo, useState } from 'react'
import en from './locales/en.json'
import sw from './locales/sw.json'
import lg from './locales/lg.json'
import nyn from './locales/nyn.json'
import ach from './locales/ach.json'
import teo from './locales/teo.json'

export const LANGUAGES = [
  { code: 'en', name: 'English', review: 'source' },
  { code: 'sw', name: 'Kiswahili', review: 'draft' },
  { code: 'lg', name: 'Luganda', review: 'draft' },
  { code: 'nyn', name: 'Runyankole', review: 'partial' },
  { code: 'ach', name: 'Acholi', review: 'partial' },
  { code: 'teo', name: 'Ateso', review: 'partial' },
]
const DICTS = { en, sw, lg, nyn, ach, teo }

function lookup(dict, key) {
  return key.split('.').reduce((o, k) => (o && typeof o === 'object' ? o[k] : undefined), dict)
}

export function translate(lang, key, vars) {
  let text = lookup(DICTS[lang] || {}, key)
  if (typeof text !== 'string') text = lookup(en, key)
  if (typeof text !== 'string') return key
  if (vars) text = text.replace(/\{(\w+)\}/g, (_, k) => (vars[k] ?? `{${k}}`))
  return text
}

const I18nContext = createContext(null)

function initialLang() {
  try {
    const saved = localStorage.getItem('tlw_lang') // language preference only — never case data
    if (saved && DICTS[saved]) return saved
  } catch { /* storage unavailable */ }
  return 'en'
}

export function I18nProvider({ children }) {
  const [lang, setLangState] = useState(initialLang)
  const setLang = useCallback((l) => {
    if (!DICTS[l]) return
    setLangState(l)
    document.documentElement.lang = l
    try { localStorage.setItem('tlw_lang', l) } catch { /* ignore */ }
  }, [])
  const t = useCallback((key, vars) => translate(lang, key, vars), [lang])
  const value = useMemo(() => ({ lang, setLang, t, isDraft: lang !== 'en' }), [lang, setLang, t])
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}

export const useI18n = () => useContext(I18nContext)
export const useT = () => useContext(I18nContext).t
