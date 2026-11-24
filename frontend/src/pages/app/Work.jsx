import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api, describeError } from '../../api/client'
import { Alert, Badge, Button, Card, EmptyState, ErrorState, Field, Loading, Modal, PageHeader, Select, StatusBadge, Tabs, Textarea } from '../../components/ui'
import { useApi } from '../../hooks/useApi'
import { useI18n } from '../../i18n'
import { fmtDateTime } from '../../lib/format'
import { FollowUpList } from './CaseDetail'

export function Appointments() {
  const { t, lang } = useI18n()
  const [upcoming, setUpcoming] = useState('1')
  const { data, error, loading, reload } = useApi('/appointments/', { params: { upcoming: upcoming === '1' ? 1 : undefined, ordering: upcoming === '1' ? 'scheduled_for' : '-scheduled_for', page_size: 50 } })
  return (
    <>
      <PageHeader title={t('appointments.title')} subtitle={t('appointments.subtitle')} />
      <Tabs value={upcoming} onChange={setUpcoming} tabs={[{ id: '1', label: t('appointments.upcoming') }, { id: '0', label: t('appointments.all') }]} />
      <Card>
        {loading && !data ? <Loading /> : error ? <div className="p-4"><ErrorState error={error} onRetry={reload} /></div>
          : data.results.length === 0 ? <EmptyState icon="calendar" title={t('appointments.empty')} /> : (
            <ul className="divide-y divide-line">
              {data.results.map((a) => (
                <li key={a.id}><Link to={`/app/cases/${a.case_id}?tab=appointments`} className="flex flex-wrap items-center gap-3 px-5 py-3.5 hover:bg-ivory">
                  <div className="min-w-0 flex-1">
                    <p className="font-semibold text-navy">{t(`appointmentType.${a.type}`)} · {fmtDateTime(a.scheduled_for, lang)}</p>
                    <p className="text-sm text-muted"><span className="font-mono">{a.case_reference}</span> · {a.public_location} · {a.institution.name}</p>
                  </div>
                  {a.reminder_sent_at && <Badge tone="success">{t('appointments.reminderSent')}</Badge>}
                  <StatusBadge status={a.status} group="appointmentStatus" />
                </Link></li>
              ))}
            </ul>
          )}
      </Card>
    </>
  )
}

export function FollowUps() {
  const { t, lang } = useI18n()
  const [mine, setMine] = useState('1')
  const [status, setStatus] = useState('PENDING')
  const { data, error, loading, reload } = useApi('/follow-ups/', { params: { mine: mine === '1' ? 1 : undefined, status, page_size: 100 } })
  return (
    <>
      <PageHeader title={t('followUps.title')} subtitle={t('followUps.subtitle')} />
      <Tabs value={mine} onChange={setMine} tabs={[{ id: '1', label: t('followUps.mine') }, { id: '0', label: t('followUps.institution') }]} />
      <Card>
        <div className="border-b border-line p-4"><div className="w-full sm:w-56"><Select aria-label={t('followUps.status')} value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="PENDING">{t('followUpStatus.PENDING')}</option><option value="DONE">{t('followUpStatus.DONE')}</option><option value="">{t('common.all')}</option>
        </Select></div></div>
        {loading && !data ? <Loading /> : error ? <div className="p-4"><ErrorState error={error} onRetry={reload} /></div>
          : data.results.length === 0 ? <EmptyState icon="check" title={t('followUps.empty')} /> : <FollowUpList items={data.results} onChanged={reload} lang={lang} showCase />}
      </Card>
    </>
  )
}

export function Reviews() {
  const { t, lang } = useI18n()
  const { data, error, loading, reload } = useApi('/case-updates/pending-review/')
  const [busy, setBusy] = useState(null)
  const [edits, setEdits] = useState({})
  const review = async (u, approve) => {
    setBusy(u.id)
    try {
      const body = { approve }
      if (edits[u.id] && edits[u.id] !== u.beneficiary_message) body.beneficiary_message = edits[u.id]
      await api.post(`/case-updates/${u.id}/review/`, body); reload()
    } catch (e) { window.alert(describeError(e, t).message) } finally { setBusy(null) }
  }
  return (
    <>
      <PageHeader title={t('reviews.title')} subtitle={t('reviews.subtitle')} />
      <div className="mb-5"><Alert tone="bronze" title={t('reviews.ruleTitle')}>{t('reviews.rule')}</Alert></div>
      {loading ? <Loading /> : error ? <ErrorState error={error} onRetry={reload} /> : data.length === 0 ? <Card><EmptyState icon="check" title={t('reviews.empty')} /></Card> : (
        <div className="space-y-4">
          {data.map((u) => (
            <Card key={u.id} className="p-5">
              <div className="flex flex-wrap items-center gap-2 text-sm text-muted">
                <Link to={`/app/cases/${u.case_id}?tab=timeline`} className="font-mono font-semibold text-teal hover:underline">{u.case_reference}</Link>
                <span>· {u.institution.name} · {u.author.full_name} · {fmtDateTime(u.created_at, lang)}</span>
                {u.system_generated && <Badge tone="neutral" icon={null}>{t('timeline.automatic')}</Badge>}
              </div>
              <p className="mt-2 text-sm text-muted">{t('reviews.internalContext')}: {u.note}</p>
              <Field label={t('reviews.messageToFamily')} hint={t('reviews.editHint')}>
                {(a) => <Textarea {...a} maxLength={400} value={edits[u.id] ?? u.beneficiary_message} onChange={(e) => setEdits({ ...edits, [u.id]: e.target.value })} />}
              </Field>
              {u.beneficiary_journey_step && <p className="mt-2 text-xs text-muted">{t('caseDetail.journeyStep')}: {t(`journey.${u.beneficiary_journey_step}`)}</p>}
              <div className="mt-3 flex gap-2">
                <Button variant="teal" icon="check" busy={busy === u.id} onClick={() => review(u, true)}>{t('timeline.approve')}</Button>
                <Button variant="secondary" disabled={busy === u.id} onClick={() => review(u, false)}>{t('timeline.reject')}</Button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </>
  )
}

export function AssistanceRequests() {
  const { t, lang } = useI18n()
  const [status, setStatus] = useState('OPEN')
  const { data, error, loading, reload } = useApi('/assistance-requests/', { params: { status, page_size: 50 } })
  const [open, setOpen] = useState(null)
  const [form, setForm] = useState({ status: 'RESOLVED', response_message: '' })
  const [err, setErr] = useState(null)
  const [busy, setBusy] = useState(false)
  const submit = async () => {
    setBusy(true); setErr(null)
    try { await api.post(`/assistance-requests/${open.id}/respond/`, form); setOpen(null); reload() } catch (e) { setErr(describeError(e, t)) } finally { setBusy(false) }
  }
  return (
    <>
      <PageHeader title={t('assistance.title')} subtitle={t('assistance.subtitle')} />
      <Tabs value={status} onChange={setStatus} tabs={['OPEN', 'IN_PROGRESS', 'RESOLVED', ''].map((s) => ({ id: s, label: s ? t(`assistanceStatus.${s}`) : t('common.all') }))} />
      <Card>
        {loading && !data ? <Loading /> : error ? <div className="p-4"><ErrorState error={error} onRetry={reload} /></div>
          : data.results.length === 0 ? <EmptyState icon="help" title={t('assistance.empty')} /> : (
            <ul className="divide-y divide-line">
              {data.results.map((r) => (
                <li key={r.id} className="flex flex-wrap items-center gap-3 px-5 py-4">
                  <div className="min-w-0 flex-1">
                    <p className="font-semibold text-navy">{t(`assistanceType.${r.request_type}`)}</p>
                    <p className="text-sm text-muted"><Link to={`/app/cases/${r.case_id}?tab=family`} className="font-mono text-teal hover:underline">{r.case_reference}</Link> · {r.requested_by.full_name}{r.requested_by.relationship && ` (${t(`relationship.${r.requested_by.relationship}`)})`} · {fmtDateTime(r.created_at, lang)}</p>
                    {r.message && <p className="mt-1 text-sm text-ink">“{r.message}”</p>}
                    {r.preferred_contact_time && <p className="text-xs text-muted">{t('assistance.contactTime')}: {r.preferred_contact_time}</p>}
                    {r.response_message && <p className="mt-1 text-sm text-success-700">{t('assistance.yourResponse')}: {r.response_message}</p>}
                  </div>
                  {r.request_type === 'SAFETY_CONCERN' && <Badge tone="danger">{t('assistance.safety')}</Badge>}
                  <StatusBadge status={r.status} group="assistanceStatus" />
                  {r.status !== 'CLOSED' && <Button size="sm" onClick={() => { setOpen(r); setForm({ status: 'RESOLVED', response_message: r.response_message || '' }) }}>{t('assistance.respond')}</Button>}
                </li>
              ))}
            </ul>
          )}
      </Card>
      <Modal open={!!open} onClose={() => setOpen(null)} title={t('assistance.respond')}>
        <Field label={t('assistance.newStatus')}>{(a) => <Select {...a} value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
          {['IN_PROGRESS', 'RESOLVED', 'CLOSED'].map((s) => <option key={s} value={s}>{t(`assistanceStatus.${s}`)}</option>)}</Select>}</Field>
        <Field label={t('assistance.responseLabel')} hint={t('assistance.responseHint')} error={err?.fields?.response_message}>
          {(a) => <Textarea {...a} maxLength={500} value={form.response_message} onChange={(e) => setForm({ ...form, response_message: e.target.value })} />}
        </Field>
        {err && !err.fields?.response_message && <Alert tone="danger">{err.message}</Alert>}
        <div className="flex justify-end gap-2"><Button variant="secondary" onClick={() => setOpen(null)}>{t('common.cancel')}</Button><Button busy={busy} onClick={submit}>{t('common.save')}</Button></div>
      </Modal>
    </>
  )
}

export function Notifications({ beneficiary }) {
  const { t, lang } = useI18n()
  const { data, error, loading, reload } = useApi('/notifications/', { params: { page_size: 50 } })
  const markAll = async () => { await api.post('/notifications/read-all/'); reload() }
  const open = async (n) => { if (!n.is_read) { await api.post(`/notifications/${n.id}/read/`); reload() } }
  const body = loading && !data ? <Loading /> : error ? <div className="p-4"><ErrorState error={error} onRetry={reload} /></div>
    : data.results.length === 0 ? <EmptyState icon="bell" title={t('notifications.empty')} /> : (
      <ul className="divide-y divide-line">
        {data.results.map((n) => {
          const inner = (
            <div className="flex items-start gap-3 px-5 py-4">
              <span className={`mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full ${n.is_read ? 'bg-line' : 'bg-bronze'}`} aria-label={n.is_read ? t('notifications.read') : t('notifications.unread')} />
              <div className="min-w-0 flex-1">
                <p className={`text-ink ${n.is_read ? '' : 'font-semibold'}`}>{n.title}</p>
                <p className="text-sm text-muted">{n.body}</p>
                <p className="mt-1 text-xs text-muted">{fmtDateTime(n.created_at, lang)}</p>
              </div>
            </div>
          )
          return <li key={n.id}>{n.link ? <Link to={n.link} onClick={() => open(n)} className="block hover:bg-ivory">{inner}</Link> : <button className="block w-full text-left hover:bg-ivory" onClick={() => open(n)}>{inner}</button>}</li>
        })}
      </ul>
    )
  return (
    <>
      <PageHeader title={beneficiary ? t('ben.nav.messages') : t('notifications.title')} subtitle={t('notifications.subtitle')}
        actions={<Button variant="secondary" size="sm" onClick={markAll}>{t('notifications.markAll')}</Button>} />
      <Card>{body}</Card>
    </>
  )
}

