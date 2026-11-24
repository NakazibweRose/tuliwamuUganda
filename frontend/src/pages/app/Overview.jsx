import { Link } from 'react-router-dom'
import { useAuth } from '../../auth/AuthContext'
import { Badge, Card, CardHeader, EmptyState, ErrorState, Icon, Loading, PageHeader, PriorityBadge, StatusBadge } from '../../components/ui'
import { useApi } from '../../hooks/useApi'
import { useI18n } from '../../i18n'
import { fmtDate, fmtDateTime } from '../../lib/format'

function Tile({ to, icon, label, value, tone = 'teal' }) {
  const toneCls = { teal: 'bg-teal-50 text-teal', bronze: 'bg-bronze-50 text-bronze', warn: 'bg-warn-50 text-warn-700', navy: 'bg-sage-50 text-deep' }[tone]
  return (
    <Link to={to} className="group flex items-center gap-4 rounded-xl border border-line bg-white p-4 shadow-card transition hover:border-teal">
      <span className={`rounded-xl p-3 ${toneCls}`}><Icon name={icon} /></span>
      <span className="min-w-0">
        <span className="block font-serif text-2xl font-semibold text-navy tabular-nums">{value ?? '…'}</span>
        <span className="block truncate text-sm text-muted group-hover:text-ink">{label}</span>
      </span>
    </Link>
  )
}

function AdminOverview() {
  const { t } = useI18n()
  const users = useApi('/admin/users/', { params: { page_size: 1 } })
  const inst = useApi('/institutions/', { params: { page_size: 1 } })
  const sec = useApi('/audit-logs/', { params: { is_security_event: true, page_size: 6 } })
  return (
    <>
      <PageHeader title={t('overview.adminTitle')} subtitle={t('overview.adminSubtitle')} />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Tile to="/app/admin/users" icon="users" label={t('nav.users')} value={users.data?.count} />
        <Tile to="/app/admin/institutions" icon="home" label={t('nav.institutions')} value={inst.data?.count} tone="navy" />
        <Tile to="/app/analytics" icon="chart" label={t('nav.analytics')} value="→" tone="bronze" />
        <Tile to="/app/admin/audit" icon="shield" label={t('overview.securityEvents')} value={sec.data?.count} tone="warn" />
      </div>
      <Card className="mt-6">
        <CardHeader title={t('overview.recentSecurity')} subtitle={t('overview.adminNoCaseAccess')} />
        {sec.loading ? <Loading /> : sec.error ? <div className="p-4"><ErrorState error={sec.error} /></div> : (
          <ul className="divide-y divide-line">
            {sec.data.results.map((e) => (
              <li key={e.id} className="flex flex-wrap items-center justify-between gap-2 px-5 py-3 text-sm">
                <span className="font-mono text-xs">{e.action}</span>
                <span className="text-muted">{e.actor || t('common.anonymous')} · {fmtDateTime(e.created_at)}</span>
                <Badge tone={e.success ? 'neutral' : 'danger'}>{e.success ? t('common.ok') : t('common.failed')}</Badge>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </>
  )
}

export default function Overview() {
  const { user } = useAuth()
  const { t, lang } = useI18n()
  const isAdmin = user.role === 'ADMIN'
  const cases = useApi(isAdmin ? null : '/cases/', { params: { page_size: 5 } })
  const incoming = useApi(isAdmin ? null : '/referrals/', { params: { direction: 'incoming', status: 'SENT', page_size: 6 } })
  const appts = useApi(isAdmin ? null : '/appointments/', { params: { upcoming: 1, page_size: 5, ordering: 'scheduled_for' } })
  const reviews = useApi(isAdmin ? null : '/case-updates/pending-review/')
  const followups = useApi(isAdmin ? null : '/follow-ups/', { params: { mine: 1, status: 'PENDING', page_size: 1 } })

  if (isAdmin) return <AdminOverview />

  return (
    <>
      <PageHeader title={t('overview.greeting', { name: (user.full_name || user.username).split(' ').slice(-1)[0] })}
        subtitle={user.institution?.name}
        actions={user.permissions.register_case && <Link to="/app/cases/new" className="inline-flex min-h-[44px] items-center gap-2 rounded-lg bg-navy px-4 font-semibold text-white hover:bg-deep"><Icon name="plus" className="h-4 w-4" />{t('cases.new')}</Link>} />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Tile to="/app/cases" icon="folder" label={t('overview.myCases')} value={cases.data?.count} />
        <Tile to="/app/referrals?direction=incoming" icon="send" label={t('overview.awaitingAck')} value={incoming.data?.count} tone="warn" />
        <Tile to="/app/reviews" icon="eye" label={t('overview.pendingReviews')} value={reviews.data?.length} tone="bronze" />
        <Tile to="/app/follow-ups" icon="list" label={t('overview.myFollowUps')} value={followups.data?.count} tone="navy" />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader title={t('overview.incomingTitle')} subtitle={t('overview.incomingSubtitle')} />
          {incoming.loading ? <Loading /> : incoming.error ? <div className="p-4"><ErrorState error={incoming.error} onRetry={incoming.reload} /></div>
            : incoming.data.results.length === 0 ? <EmptyState icon="check" title={t('overview.noIncoming')} /> : (
              <ul className="divide-y divide-line">
                {incoming.data.results.map((r) => (
                  <li key={r.id}><Link to={`/app/referrals/${r.id}`} className="flex items-center gap-3 px-5 py-3 hover:bg-ivory">
                    <div className="min-w-0 flex-1">
                      <p className="font-semibold text-navy">{t(`referralCategory.${r.category}`)} · <span className="font-mono text-sm">{r.reference}</span></p>
                      <p className="truncate text-sm text-muted">{t('referrals.from')} {r.sending_institution.name} · {fmtDate(r.sent_at, lang)}</p>
                    </div>
                    <PriorityBadge priority={r.priority} />
                  </Link></li>
                ))}
              </ul>
            )}
        </Card>
        <Card>
          <CardHeader title={t('overview.upcomingTitle')} />
          {appts.loading ? <Loading /> : appts.error ? <div className="p-4"><ErrorState error={appts.error} /></div>
            : appts.data.results.length === 0 ? <EmptyState icon="calendar" title={t('overview.noAppointments')} /> : (
              <ul className="divide-y divide-line">
                {appts.data.results.map((a) => (
                  <li key={a.id}><Link to={`/app/cases/${a.case_id}?tab=appointments`} className="flex items-center gap-3 px-5 py-3 hover:bg-ivory">
                    <div className="w-14 shrink-0 rounded-lg bg-ivory py-1 text-center">
                      <p className="text-[11px] font-semibold uppercase text-muted">{new Date(a.scheduled_for).toLocaleDateString('en-GB', { month: 'short' })}</p>
                      <p className="font-serif text-xl font-semibold text-navy">{new Date(a.scheduled_for).getDate()}</p>
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="font-semibold text-navy">{t(`appointmentType.${a.type}`)}</p>
                      <p className="truncate text-sm text-muted">{a.case_reference} · {fmtDateTime(a.scheduled_for, lang)}</p>
                    </div>
                    <StatusBadge status={a.status} group="appointmentStatus" />
                  </Link></li>
                ))}
              </ul>
            )}
        </Card>
      </div>

      <Card className="mt-6">
        <CardHeader title={t('overview.recentCases')} action={<Link to="/app/cases" className="text-sm font-semibold text-teal">{t('common.viewAll')}</Link>} />
        {cases.loading ? <Loading /> : cases.error ? <div className="p-4"><ErrorState error={cases.error} /></div>
          : cases.data.results.length === 0 ? <EmptyState icon="folder" title={t('cases.empty')}>{t('cases.emptyHint')}</EmptyState> : (
            <ul className="divide-y divide-line">
              {cases.data.results.map((c) => (
                <li key={c.id}><Link to={`/app/cases/${c.id}`} className="flex flex-wrap items-center gap-3 px-5 py-3 hover:bg-ivory">
                  <span className="font-mono text-sm font-semibold text-navy">{c.reference}</span>
                  <span className="text-sm text-ink">{c.child_pseudonym}</span>
                  {c.immediate_risk && <Badge tone="danger">{t('cases.immediateRisk')}</Badge>}
                  <span className="flex-1" />
                  <Badge tone="info" icon={null}>{t(`stage.${c.stage.code}`)}</Badge>
                </Link></li>
              ))}
            </ul>
          )}
      </Card>
    </>
  )
}
