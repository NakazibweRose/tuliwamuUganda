import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { DraftTranslationNotice, LanguageSelect, Logo, OfflineBanner, QuickExitButton } from '../components/common'
import { Suspense } from 'react'
import { Icon, Loading } from '../components/ui'
import { useT } from '../i18n'

const ITEMS = [
  { to: '/me', icon: 'home', key: 'home', end: true },
  { to: '/me/help', icon: 'msg', key: 'help' },
  { to: '/me/support', icon: 'heart', key: 'support' },
  { to: '/me/messages', icon: 'bell', key: 'messages' },
  { to: '/me/settings', icon: 'settings', key: 'settings' },
]

export default function BeneficiaryLayout() {
  const t = useT()
  const { logout, user } = useAuth()
  // The USSD reporting simulator is only for complainants (the people who report).
  const items = user.permissions?.ussd_simulator
    ? [...ITEMS.slice(0, 2), { to: '/me/ussd', icon: 'phoneSim', key: 'ussd' }, ...ITEMS.slice(2)]
    : ITEMS
  const navigate = useNavigate()
  return (
    <div className="min-h-screen bg-ivory pb-20 sm:pb-0">
      <OfflineBanner />
      <header className="sticky top-0 z-20 border-b border-line bg-white">
        <DraftTranslationNotice />
        <div className="mx-auto flex h-16 max-w-3xl items-center gap-2 px-4">
          <NavLink to="/me" aria-label="Tuliwamu"><Logo small compact /></NavLink>
          <div className="flex-1" />
          <LanguageSelect compact onChange={(l) => api.patch('/auth/me/', { preferred_language: l }).catch(() => {})} />
          <QuickExitButton />
        </div>
        <nav className="mx-auto hidden max-w-3xl gap-1 px-4 sm:flex" aria-label={t('nav.main')}>
          {items.map((i) => (
            <NavLink key={i.to} to={i.to} end={i.end} className={({ isActive }) => `flex min-h-[44px] items-center gap-2 border-b-2 px-3 text-sm font-semibold ${isActive ? 'border-teal text-navy' : 'border-transparent text-muted hover:text-ink'}`}>
              <Icon name={i.icon} className="h-4 w-4" />{t(`ben.nav.${i.key}`)}
            </NavLink>
          ))}
          <div className="flex-1" />
          <button onClick={async () => { await logout(); navigate('/login') }} className="text-sm font-semibold text-muted hover:text-ink">{t('nav.signOut')}</button>
        </nav>
      </header>
      <main id="main" className="mx-auto max-w-3xl px-4 py-6"><Suspense fallback={<Loading />}><Outlet /></Suspense></main>
      <nav className={`fixed inset-x-0 bottom-0 z-20 grid ${items.length > 5 ? 'grid-cols-6' : 'grid-cols-5'} border-t border-line bg-white sm:hidden`} aria-label={t('nav.main')}>
        {items.map((i) => (
          <NavLink key={i.to} to={i.to} end={i.end} className={({ isActive }) => `flex min-h-[60px] flex-col items-center justify-center gap-0.5 text-[11px] font-semibold ${isActive ? 'text-teal' : 'text-muted'}`}>
            <Icon name={i.icon} className="h-5 w-5" />{t(`ben.nav.${i.key}`)}
          </NavLink>
        ))}
      </nav>
    </div>
  )
}
