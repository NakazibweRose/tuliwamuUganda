import { useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { api, describeError } from '../../api/client'
import { Alert, Badge, Button, Card, CardHeader, Detail, EmptyState, ErrorState, Field, Icon, Loading, Modal, PageHeader, PriorityBadge, Select, StatusBadge, Table, Tabs, Textarea } from '../../components/ui'
import { useApi } from '../../hooks/useApi'
import { useI18n } from '../../i18n'
import { fmtDate, fmtDateTime } from '../../lib/format'
import { REFERRAL_CATEGORIES } from '../../lib/labels'

export function ReferralList() {
  const { t, lang } = useI18n()
  const [params, setParams] = useSearchParams()
  const direction = params.get('direction') || 'incoming'
  const [status, setStatus] = useState('')
  const [category, setCategory] = useState('')
  const { data, error, loading, reload } = useApi('/referrals/', { params: { direction, status, category, page_size: 50 } })
  return (
    <>
      <PageHeader title={t('referrals.title')} subtitle={t('referrals.subtitle')} />
      <Tabs value={direction} onChange={(v) => setParams({ direction: v })}
        tabs={[{ id: 'incoming', label: t('referrals.incoming') }, { id: 'outgoing', label: t('referrals.outgoing') }]} />
      <Card>
        <div className="flex flex-wrap gap-3 border-b border-line p-4">
          <div className="w-full sm:w-56"><Select aria-label={t('referrals.status')} value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">{t('referrals.allStatuses')}</option>
            {['SENT', 'ACKNOWLEDGED', 'IN_PROGRESS', 'COMPLETED', 'RETURNED', 'DECLINED', 'CANCELLED'].map((s) => <option key={s} value={s}>{t(`referralStatus.${s}`)}</option>)}
          </Select></div>
          <div className="w-full sm:w-56"><Select aria-label={t('referrals.category')} value={category} onChange={(e) => setCategory(e.target.value)}>
            <option value="">{t('referrals.allCategories')}</option>
            {REFERRAL_CATEGORIES.map((s) => <option key={s} value={s}>{t(`referralCategory.${s}`)}</option>)}
          </Select></div>
        </div>
        {loading && !data ? <Loading /> : error ? <div className="p-4"><ErrorState error={error} onRetry={reload} /></div>
          : data.results.length === 0 ? <EmptyState icon="send" title={t('referrals.empty')} /> : (
            <Table head={[t('referrals.reference'), t('referrals.category'), direction === 'incoming' ? t('referrals.fromCol') : t('referrals.toCol'), t('referrals.case'), t('referrals.sent'), t('referrals.priority'), t('referrals.status')]}>
              {data.results.map((r) => (
                <tr key={r.id} className="hover:bg-ivory/70">
                  <td className="px-4 py-3"><Link to={`/app/referrals/${r.id}`} className="font-mono font-semibold text-navy hover:underline">{r.reference}</Link></td>
                  <td className="px-4 py-3">{t(`referralCategory.${r.category}`)}</td>
                  <td className="px-4 py-3 text-muted">{direction === 'incoming' ? r.sending_institution.name : r.receiving_institution.name}</td>
                  <td className="px-4 py-3 font-mono text-xs">{r.case_reference}</td>
                  <td className="whitespace-nowrap px-4 py-3 text-muted">{fmtDate(r.sent_at, lang)}</td>
                  <td className="px-4 py-3"><PriorityBadge priority={r.priority} /></td>
                  <td className="px-4 py-3"><StatusBadge status={r.status} group="referralStatus" /></td>
                </tr>
              ))}
            </Table>
          )}
      </Card>
    </>
  )
}

const ACTION_STYLE = { acknowledge: 'teal', start: 'secondary', complete: 'teal', return: 'secondary', decline: 'danger', cancel: 'secondary', send: 'primary', resend: 'primary' }
const NEEDS_NOTE = ['return', 'decline', 'cancel', 'resend']

export function ReferralDetail() {
  const { id } = useParams()
  const { t, lang } = useI18n()
  const { data: r, error, loading, reload } = useApi(`/referrals/${id}/`)
  const [pending, setPending] = useState(null)
  const [form, setForm] = useState({ note: '', outcome_summary: '', restricted_notes: '' })
  const [actErr, setActErr] = useState(null)
  const [busy, setBusy] = useState(false)

  if (loading) return <Loading />
  if (error) return <ErrorState error={error} onRetry={reload} />

  const run = async (action, body = {}) => {
    setBusy(true); setActErr(null)
    try { await api.post(`/referrals/${r.id}/${action}/`, body); setPending(null); setForm({ note: '', outcome_summary: '', restricted_notes: '' }); reload() }
    catch (e) { setActErr(describeError(e, t)) } finally { setBusy(false) }
  }
  const click = (a) => (NEEDS_NOTE.includes(a) || a === 'complete' ? setPending(a) : run(a))
  const isReceiver = r.direction === 'incoming'

  return (
    <>
      <PageHeader
        back={<Link to={`/app/referrals?direction=${r.direction}`} className="mb-2 inline-flex items-center gap-1 text-sm font-semibold text-teal"><Icon name="arrowLeft" className="h-4 w-4" />{t('nav.referrals')}</Link>}
        title={<><span className="font-mono">{r.reference}</span> · {t(`referralCategory.${r.category}`)}</>}
        subtitle={`${r.sending_institution.name} → ${r.receiving_institution.name}`}
        actions={r.actions.map((a) => <Button key={a} variant={ACTION_STYLE[a]} busy={busy && !pending} onClick={() => click(a)}>{t(`referralAction.${a}`)}</Button>)}
      />
      <div className="mb-5 flex flex-wrap gap-2"><StatusBadge status={r.status} group="referralStatus" /><PriorityBadge priority={r.priority} />
        <Badge tone="neutral" icon={null}>{isReceiver ? t('referrals.incoming') : t('referrals.outgoing')}</Badge></div>
      {actErr && !pending && <div className="mb-4"><Alert tone="danger">{actErr.message}</Alert></div>}
      {isReceiver && r.status === 'SENT' && <div className="mb-5"><Alert tone="warn" title={t('referralDetail.ackTitle')}>{t('referralDetail.ackBody')}</Alert></div>}

      <div className="grid gap-6 lg:grid-cols-[1fr_22rem]">
        <div className="space-y-6">
          <Card>
            <CardHeader title={t('referralDetail.purpose')} />
            <p className="px-5 py-4 text-ink">{r.purpose}</p>
          </Card>
          <Card>
            <CardHeader title={t('referralDetail.shared')} subtitle={t('referralDetail.sharedHint')} />
            {r.shared_fields.length === 0 ? <p className="px-5 py-4 text-sm text-muted">{t('referralDetail.nothingShared')}</p> : (
              <dl className="grid gap-4 p-5 sm:grid-cols-2">
                {r.shared_fields.map((f) => (
                  <Detail key={f} label={t(`shareable.${f}`)}>{formatShared(f, r.shared_data[f], t)}</Detail>
                ))}
              </dl>
            )}
          </Card>
          {(r.outcome_summary || r.restricted_notes) && (
            <Card>
              <CardHeader title={t('referralDetail.outcome')} />
              <div className="space-y-4 p-5">
                <Detail label={t('referralDetail.outcomeSummary')}>{r.outcome_summary || '—'}</Detail>
                {r.restricted_notes != null && (
                  <div className="rounded-xl border border-bronze/30 bg-bronze-50 p-4">
                    <p className="mb-1 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-[#6b5636]"><Icon name="shield" className="h-4 w-4" />{t('referralDetail.restrictedNotes')}</p>
                    <p className="text-sm text-ink">{r.restricted_notes || '—'}</p>
                  </div>
                )}
              </div>
            </Card>
          )}
        </div>
        <div className="space-y-6">
          <Card>
            <CardHeader title={t('referralDetail.details')} />
            <dl className="space-y-4 p-5">
              <Detail label={t('referrals.case')}>{r.case_on_team ? <Link className="font-mono text-teal hover:underline" to={`/app/cases/${r.case_id}`}>{r.case_reference}</Link> : <span className="font-mono">{r.case_reference}</span>}</Detail>
              <Detail label={t('referralDetail.sentBy')}>{r.sent_by.full_name}</Detail>
              <Detail label={t('referralDetail.assigned')}>{r.assigned_officer?.full_name || '—'}</Detail>
              <Detail label={t('referrals.sent')}>{fmtDateTime(r.sent_at, lang)}</Detail>
              <Detail label={t('referralDetail.acknowledged')}>{fmtDateTime(r.acknowledged_at, lang)}</Detail>
              <Detail label={t('referralDetail.completed')}>{fmtDateTime(r.completed_at, lang)}</Detail>
            </dl>
            {!r.case_on_team && <div className="px-5 pb-5"><Alert>{t('referralDetail.snapshotOnly')}</Alert></div>}
          </Card>
          <Card>
            <CardHeader title={t('referralDetail.history')} />
            <ol className="space-y-3 p-5">
              {r.history.map((h) => (
                <li key={h.id} className="text-sm">
                  <p className="font-semibold text-ink">{h.from_status ? `${t(`referralStatus.${h.from_status}`)} → ` : ''}{t(`referralStatus.${h.to_status}`)}</p>
                  <p className="text-xs text-muted">{fmtDateTime(h.created_at, lang)} · {h.actor.full_name} · {h.institution.name}</p>
                  {h.note && <p className="mt-0.5 text-muted">“{h.note}”</p>}
                </li>
              ))}
            </ol>
          </Card>
        </div>
      </div>

      <Modal open={!!pending} onClose={() => { setPending(null); setActErr(null) }} title={pending ? t(`referralAction.${pending}`) : ''}>
        {pending === 'complete' ? (
          <>
            <Field label={t('referralDetail.outcomeSummary')} hint={t('referralDetail.outcomeSummaryHint')} required error={actErr?.fields?.outcome_summary}>
              {(a) => <Textarea {...a} maxLength={500} value={form.outcome_summary} onChange={(e) => setForm({ ...form, outcome_summary: e.target.value })} />}
            </Field>
            <Field label={t('referralDetail.restrictedNotes')} hint={t('referralDetail.restrictedNotesHint')}>
              {(a) => <Textarea {...a} value={form.restricted_notes} onChange={(e) => setForm({ ...form, restricted_notes: e.target.value })} />}
            </Field>
            <Alert tone="bronze">{t('referralDetail.completeFamilyNote')}</Alert>
          </>
        ) : (
          <Field label={t('referralDetail.reason')} required error={actErr?.fields?.note}>
            {(a) => <Textarea {...a} maxLength={500} value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} />}
          </Field>
        )}
        {actErr && !actErr.fields?.note && !actErr.fields?.outcome_summary && <Alert tone="danger">{actErr.message}</Alert>}
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setPending(null)}>{t('common.cancel')}</Button>
          <Button variant={ACTION_STYLE[pending]} busy={busy} onClick={() => run(pending, pending === 'complete' ? { outcome_summary: form.outcome_summary, restricted_notes: form.restricted_notes } : { note: form.note })}>{t('common.confirm')}</Button>
        </div>
      </Modal>
    </>
  )
}

function formatShared(field, value, t) {
  if (value === null || value === undefined || value === '') return '—'
  if (field === 'age_range') return t(`age.${value}`)
  if (field === 'incident_category') return t(`incident.${value}`)
  if (field === 'preferred_language') return t(`languages.${value}`)
  if (field === 'immediate_risk') return value ? t('common.yes') : t('common.no')
  return String(value)
}
