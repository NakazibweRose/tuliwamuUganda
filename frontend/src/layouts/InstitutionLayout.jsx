import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { DraftTranslationNotice, LanguageSelect, Logo, OfflineBanner } from '../components/common'
import { Suspense } from 'react'
import { Icon, Loading } from '../components/ui'
import { useT } from '../i18n'

function navFor(user) {
  const p = user.permissions || {}
  const isAdmin = user.role === 'ADMIN'
  const items = []
  items.push({ to: '/app', icon: 'home', key: 'overview', end: true })
  if (!isAdmin) {
    items.push({ to: '/app/cases', icon: 'folder', key: 'cases' })
    items.push({ to: '/app/referrals', icon: 'send', key: 'referrals' })
    items.push({ to: '/app/appointments', icon: 'calendar', key: 'appointments' })
    items.push({ to: '/app/follow-ups', icon: 'list', key: 'followUps' })
    items.push({ to: '/app/reviews', icon: 'eye', key: 'reviews' })
    items.push({ to: '/app/assistance', icon: 'help', key: 'assistance' })
  }
  if (p.triage_anonymous_reports) items.push({ to: '/app/anonymous-reports', icon: 'shield', key: 'anonymousReports' })
  if (p.view_analytics) {
    items.push({ section: 'insight' })
    items.push({ to: '/app/analytics', icon: 'chart', key: 'analytics' })
    items.push({ to: '/app/sms', icon: 'msg', key: 'sms' })
  }
  items.push({ to: '/app/ussd-simulator', icon: 'phoneSim', key: 'ussd' })
  if (isAdmin) {
    items.push({ section: 'administration' })
    items.push({ to: '/app/admin/users', icon: 'users', key: 'users' })
    items.push({ to: '/app/admin/institutions', icon: 'home', key: 'institutions' })
    items.push({ to: '/app/admin/services', icon: 'heart', key: 'services' })
    items.push({ to: '/app/admin/audit', icon: 'file', key: 'audit' })
  }
  return items
}

export default function InstitutionLayout() {
  const { user, logout } = useAuth()
  const t = useT()
  const [open, setOpen] = useState(false)
  const [unread, setUnread] = useState(0)
  const location = useLocation()
  const navigate = useNavigate()

  useEffect(() => { setOpen(false) }, [location.pathname])
  useEffect(() => {
    let alive = true
    const poll = () => api.get('/notifications/unread-count/').then((r) => alive && setUnread(r.data.unread)).catch(() => {})
    poll()
    const id = setInterval(poll, 60000)
    return () => { alive = false; clearInterval(id) }
  }, [location.pathname])

  const nav = (
    <nav className="space-y-0.5 px-3 py-4" aria-label={t('nav.main')}>
      {navFor(user).map((item, i) => item.section ? (
        <p key={i} className="px-3 pb-1 pt-4 text-[11px] font-semibold uppercase tracking-wider text-white/45">{t(`nav.${item.section}`)}</p>
      ) : (
        <NavLink key={item.to} to={item.to} end={item.end}
          className={({ isActive }) => `flex min-h-[42px] items-center gap-3 rounded-lg px-3 text-sm font-medium transition-colors ${isActive ? 'bg-white/10 text-white shadow-[inset_3px_0_0_#AD9063]' : 'text-white/75 hover:bg-white/5 hover:text-white'}`}>
          <Icon name={item.icon} className="h-[18px] w-[18px]" /> {t(`nav.${item.key}`)}
        </NavLink>
      ))}
    </nav>
  )

  return (
    <div className="min-h-screen bg-ivory">
      <OfflineBanner />
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-white focus:p-2">{t('common.skipToContent')}</a>
      <aside className={`fixed inset-y-0 left-0 z-40 w-64 transform bg-navy transition-transform lg:translate-x-0 ${open ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="flex h-16 items-center px-5"><Logo light small /></div>
        <div className="mx-3 rounded-lg bg-white/5 px-3 py-2.5">
          <p className="truncate text-sm font-semibold text-white">{user.full_name || user.username}</p>
          <p className="truncate text-xs text-white/60">{t(`roles.${user.role}`)}</p>
          {user.institution && <p className="mt-0.5 truncate text-xs text-bronze">{user.institution.name}</p>}
        </div>
        <div className="h-[calc(100vh-10rem)] overflow-y-auto">{nav}</div>
      </aside>
      {open && <div className="fixed inset-0 z-30 bg-navy/40 lg:hidden" onClick={() => setOpen(false)} />}

      <div className="lg:pl-64">
        <header className="sticky top-0 z-20 border-b border-line bg-white/95 backdrop-blur">
          <DraftTranslationNotice />
          <div className="flex h-16 items-center gap-3 px-4 sm:px-6">
            <button className="rounded-lg p-2 text-navy lg:hidden" onClick={() => setOpen(true)} aria-label={t('nav.openMenu')}><Icon name="menu" /></button>
            <div className="flex-1" />
            <LanguageSelect compact onChange={(l) => api.patch('/auth/me/', { preferred_language: l }).catch(() => {})} />
            <NavLink to="/app/notifications" className="relative rounded-lg p-2.5 text-deep hover:bg-ivory" aria-label={t('nav.notifications') + (unread ? ` (${unread})` : '')}>
              <Icon name="bell" />
              {unread > 0 && <span className="absolute right-1 top-1 min-w-[18px] rounded-full bg-bronze px-1 text-center text-[11px] font-bold leading-[18px] text-white">{unread}</span>}
            </NavLink>
            <NavLink to="/app/settings" className="rounded-lg p-2.5 text-deep hover:bg-ivory" aria-label={t('nav.settings')}><Icon name="settings" /></NavLink>
            <button onClick={async () => { await logout(); navigate('/login') }} className="hidden min-h-[40px] items-center gap-2 rounded-lg px-3 text-sm font-semibold text-deep hover:bg-ivory sm:inline-flex">
              <Icon name="logout" className="h-4 w-4" /> {t('nav.signOut')}
            </button>
          </div>
        </header>
        <main id="main" className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:py-8"><Suspense fallback={<Loading />}><Outlet /></Suspense></main>
      </div>
    </div>
  )
}
