import { useEffect, useState } from 'react'
import { LANGUAGES, useI18n } from '../i18n'
import { quickExit } from '../auth/AuthContext'
import { Icon } from './ui'

export function Logo({ light, small, compact }) {
  return (
    <span className="inline-flex items-center gap-2.5">
      <img src="/icon.svg" alt="" className={small ? 'h-8 w-8' : 'h-10 w-10'} />
      <span className={`font-serif text-xl font-semibold tracking-tight ${compact ? 'hidden min-[430px]:inline' : ''} ${light ? 'text-white' : 'text-navy'}`}>Tuliwamu</span>
    </span>
  )
}

export function LanguageSelect({ onChange, compact, dark }) {
  const { lang, setLang, t } = useI18n()
  return (
    <label className={`inline-flex items-center gap-1.5 rounded-lg border px-2 ${dark ? 'border-white/20 text-white' : 'border-line bg-white text-ink'}`}>
      <Icon name="globe" className="h-4 w-4 shrink-0" />
      <span className="sr-only">{t('common.language')}</span>
      <select value={lang} onChange={(e) => { setLang(e.target.value); onChange?.(e.target.value) }}
        className={`min-h-[40px] cursor-pointer bg-transparent py-1 pr-1 text-sm font-semibold focus:outline-none ${dark ? '[&>option]:text-ink' : ''}`}>
        {LANGUAGES.map((l) => <option key={l.code} value={l.code}>{compact ? l.code.toUpperCase() : l.name}</option>)}
      </select>
    </label>
  )
}

export function DraftTranslationNotice() {
  const { lang, t } = useI18n()
  if (lang === 'en') return null
  return (
    <div className="bg-bronze-50 px-4 py-1.5 text-center text-xs text-[#6b5636]" role="note">
      {t('common.draftTranslation')}
    </div>
  )
}

export function OfflineBanner() {
  const { t } = useI18n()
  const [online, setOnline] = useState(typeof navigator === 'undefined' ? true : navigator.onLine)
  useEffect(() => {
    const on = () => setOnline(true)
    const off = () => setOnline(false)
    window.addEventListener('online', on)
    window.addEventListener('offline', off)
    return () => { window.removeEventListener('online', on); window.removeEventListener('offline', off) }
  }, [])
  if (online) return null
  return <div className="bg-warn px-4 py-2 text-center text-sm font-semibold text-white" role="status">{t('common.offline')}</div>
}

export function QuickExitButton({ className = '' }) {
  const { t } = useI18n()
  return (
    <button onClick={quickExit} title={t('common.quickExitHint')}
      className={`inline-flex min-h-[40px] items-center gap-1.5 whitespace-nowrap rounded-lg bg-danger px-3 text-sm font-bold text-white shadow hover:bg-danger-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-danger focus-visible:ring-offset-2 ${className}`}>
      <Icon name="logout" className="h-4 w-4" /> {t('common.quickExit')}
    </button>
  )
}

export function PrototypeDisclaimer({ className = '' }) {
  const { t } = useI18n()
  return <p className={`text-xs leading-relaxed text-muted ${className}`}>{t('common.disclaimer')}</p>
}
