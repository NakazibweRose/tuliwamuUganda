import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, describeError } from '../../api/client'
import { StatTile } from '../../components/charts'
import { Alert, Badge, Button, Card, CardHeader, Detail, EmptyState, ErrorState, Field, Icon, Input, Loading, PageHeader, Select, StatusBadge, Table, Tabs, Textarea } from '../../components/ui'
import { useApi } from '../../hooks/useApi'
import { useI18n } from '../../i18n'
import { fmtDateTime } from '../../lib/format'
import { REGIONS } from '../../lib/labels'

export function AnonymousReports() {
  const { t, lang } = useI18n()
  const [status, setStatus] = useState('')
  const { data, error, loading, reload } = useApi('/anonymous-reports/', { params: { review_status: status, page_size: 50 } })
  return (
    <>
      <PageHeader title={t('anon.title')} subtitle={t('anon.subtitle')} />
      <div className="mb-5"><Alert tone="warn" title={t('anon.unverifiedTitle')}>{t('anon.unverifiedBody')}</Alert></div>
      <Tabs value={status} onChange={setStatus} tabs={['', 'URGENT', 'NEW', 'UNDER_REVIEW', 'REFERRED', 'CONVERTED', 'CLOSED'].map((s) => ({ id: s, label: s ? t(`anonStatus.${s}`) : t('common.all') }))} />
      <Card>
        {loading && !data ? <Loading /> : error ? <div className="p-4"><ErrorState error={error} onRetry={reload} /></div>
          : data.results.length === 0 ? <EmptyState icon="shield" title={t('anon.empty')} /> : (
            <Table head={[t('anon.reference'), t('anon.category'), t('anon.danger'), t('anon.location'), t('anon.received'), t('anon.status')]}>
              {data.results.map((r) => (
                <tr key={r.id} className="hover:bg-ivory/70">
                  <td className="px-4 py-3"><Link to={`/app/anonymous-reports/${r.id}`} className="font-mono font-semibold text-navy hover:underline">{r.reference_code}</Link>
                    {r.channel === 'SIMULATOR' && <span className="ml-2"><Badge tone="bronze" icon={null}>{t('anon.simulated')}</Badge></span>}</td>
                  <td className="px-4 py-3">{t(`anonCategory.${r.category}`)}</td>
                  <td className="px-4 py-3">{r.immediate_danger === 'YES' ? <Badge tone="danger">{t('common.yes')}</Badge> : t(`danger.${r.immediate_danger}`)}</td>
                  <td className="px-4 py-3">{r.general_location}</td>
                  <td className="whitespace-nowrap px-4 py-3 text-muted">{fmtDateTime(r.created_at, lang)}</td>
                  <td className="px-4 py-3"><StatusBadge status={r.review_status} group="anonStatus" /></td>
                </tr>
              ))}
            </Table>
          )}
      </Card>
    </>
  )
}

export function AnonymousReportDetail() {
  const { id } = useParams()
  const { t, lang } = useI18n()
  const { data: r, error, loading, reload, setData } = useApi(`/anonymous-reports/${id}/`)
  const insts = useApi('/institutions/', { params: { page_size: 100, is_active: true } })
  const [form, setForm] = useState({ review_status: '', verification_status: '', note: '', assigned_institution_id: '' })
  const [conv, setConv] = useState({ district: '', region: 'CENTRAL', age_range: 'UNKNOWN', child_pseudonym: '' })
  const [contact, setContact] = useState(null)
  const [err, setErr] = useState(null)
  const [busy, setBusy] = useState(false)
  if (loading) return <Loading />
  if (error) return <ErrorState error={error} onRetry={reload} />

  const post = async (path, body) => {
    setBusy(true); setErr(null)
    try { const res = await api.post(`/anonymous-reports/${r.id}/${path}/`, body); if (res.data.id) setData(res.data); return res.data }
    catch (e) { setErr(describeError(e, t)) } finally { setBusy(false) }
  }
  const review = async () => {
    const body = Object.fromEntries(Object.entries(form).filter(([, v]) => v))
    if (await post('review', body)) setForm({ review_status: '', verification_status: '', note: '', assigned_institution_id: '' })
  }
  const convert = async () => {
    const body = { district: conv.district, region: conv.region, age_range: conv.age_range }
    if (conv.child_pseudonym) body.child_pseudonym = conv.child_pseudonym
    await post('convert-to-case', body)
  }

  return (
    <>
      <PageHeader back={<Link to="/app/anonymous-reports" className="mb-2 inline-flex items-center gap-1 text-sm font-semibold text-teal"><Icon name="arrowLeft" className="h-4 w-4" />{t('nav.anonymousReports')}</Link>}
        title={<span className="font-mono">{r.reference_code}</span>} subtitle={`${t(`anonCategory.${r.category}`)} · ${r.general_location}`} />
      <div className="mb-5 flex flex-wrap gap-2"><StatusBadge status={r.review_status} group="anonStatus" /><StatusBadge status={r.verification_status} group="verification" />
        {r.immediate_danger === 'YES' && <Badge tone="danger">{t('anon.dangerNow')}</Badge>}</div>
      <div className="grid gap-6 lg:grid-cols-[1fr_24rem]">
        <div className="space-y-6">
          <Card>
            <CardHeader title={t('anon.reportTitle')} subtitle={t('anon.reportHint')} />
            <dl className="grid gap-4 p-5 sm:grid-cols-2">
              <Detail label={t('anon.received')}>{fmtDateTime(r.created_at, lang)}</Detail>
              <Detail label={t('anon.channel')}>{t(`anonChannel.${r.channel}`)}</Detail>
              <Detail label={t('anon.language')}>{t(`languages.${r.preferred_language}`)}</Detail>
              <Detail label={t('anon.danger')}>{t(`danger.${r.immediate_danger}`)}</Detail>
              <div className="sm:col-span-2"><Detail label={t('anon.description')}><span className="whitespace-pre-wrap">{r.description}</span></Detail></div>
              <Detail label={t('anon.safeContact')}>
                {!r.has_safe_contact ? t('anon.noContact') : contact ? <span className="font-mono">{contact}</span>
                  : <Button size="sm" variant="secondary" icon="eye" onClick={async () => { const d = await post('safe-contact', {}); if (d) setContact(d.safe_contact) }}>{t('anon.revealContact')}</Button>}
              </Detail>
              {r.converted_case_id && <Detail label={t('anon.convertedTo')}><Link className="font-mono text-teal hover:underline" to={`/app/cases/${r.converted_case_id}`}>{r.converted_case_reference}</Link></Detail>}
            </dl>
          </Card>
          <Card>
            <CardHeader title={t('anon.history')} />
            {r.events.length === 0 ? <p className="p-5 text-sm text-muted">{t('anon.noHistory')}</p> : (
              <ol className="space-y-3 p-5">{r.events.map((e) => (
                <li key={e.id} className="text-sm"><p className="font-semibold">{e.action.replaceAll('_', ' ').toLowerCase()}</p><p className="text-xs text-muted">{fmtDateTime(e.created_at, lang)} · {e.actor}</p>{e.note && <p className="text-muted">“{e.note}”</p>}</li>
              ))}</ol>
            )}
          </Card>
        </div>
        {r.review_status !== 'CONVERTED' && (
          <div className="space-y-6">
            <Card className="space-y-4 p-5">
              <h2 className="font-semibold text-navy">{t('anon.recordAssessment')}</h2>
              <Field label={t('anon.reviewStatus')}>{(a) => <Select {...a} value={form.review_status} onChange={(e) => setForm({ ...form, review_status: e.target.value })}>
                <option value="">—</option>{['URGENT', 'UNDER_REVIEW', 'REFERRED', 'CLOSED'].map((s) => <option key={s} value={s}>{t(`anonStatus.${s}`)}</option>)}</Select>}</Field>
              <Field label={t('anon.outcome')}>{(a) => <Select {...a} value={form.verification_status} onChange={(e) => setForm({ ...form, verification_status: e.target.value })}>
                <option value="">—</option>{['UNVERIFIED', 'CREDIBLE', 'NOT_SUBSTANTIATED', 'DUPLICATE', 'MALICIOUS'].map((s) => <option key={s} value={s}>{t(`verification.${s}`)}</option>)}</Select>}</Field>
              <Field label={t('anon.assignTo')}>{(a) => <Select {...a} value={form.assigned_institution_id} onChange={(e) => setForm({ ...form, assigned_institution_id: e.target.value })}>
                <option value="">—</option>{insts.data?.results?.map((i) => <option key={i.id} value={i.id}>{i.name}</option>)}</Select>}</Field>
              <Field label={t('anon.note')} error={err?.fields?.note}>{(a) => <Textarea {...a} maxLength={500} value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} />}</Field>
              <Button busy={busy} onClick={review} className="w-full">{t('anon.saveAssessment')}</Button>
            </Card>
            <Card className="space-y-4 p-5">
              <h2 className="font-semibold text-navy">{t('anon.convertTitle')}</h2>
              <p className="text-sm text-muted">{t('anon.convertHint')}</p>
              <Field label={t('caseNew.pseudonym')} hint={t('anon.pseudonymHint')}>{(a) => <Input {...a} value={conv.child_pseudonym} onChange={(e) => setConv({ ...conv, child_pseudonym: e.target.value })} />}</Field>
              <div className="grid grid-cols-2 gap-3">
                <Field label={t('caseNew.district')} required>{(a) => <Input {...a} value={conv.district} onChange={(e) => setConv({ ...conv, district: e.target.value })} />}</Field>
                <Field label={t('caseNew.region')}>{(a) => <Select {...a} value={conv.region} onChange={(e) => setConv({ ...conv, region: e.target.value })}>{REGIONS.map((x) => <option key={x} value={x}>{t(`region.${x}`)}</option>)}</Select>}</Field>
              </div>
              <Button variant="teal" busy={busy} disabled={r.verification_status !== 'CREDIBLE' || !conv.district} onClick={convert} className="w-full">{t('anon.convert')}</Button>
              {r.verification_status !== 'CREDIBLE' && <p className="text-xs text-muted">{t('anon.convertNeedsAssessment')}</p>}
            </Card>
            {err && !err.fields?.note && <Alert tone="danger">{err.message}</Alert>}
          </div>
        )}
      </div>
    </>
  )
}

function newSessionId() {
  return (crypto.randomUUID && crypto.randomUUID()) || 'xxxxxxxx-xxxx-4xxx-8xxx-xxxxxxxxxxxx'.replace(/x/g, () => ((Math.random() * 16) | 0).toString(16))
}

export function UssdSimulator() {
  const { t } = useI18n()
  const [session, setSession] = useState(newSessionId)
  const [text, setText] = useState('')
  const [screen, setScreen] = useState(null)
  const [ended, setEnded] = useState(false)
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)
  const [code, setCode] = useState('*384*1234#')
  const inputRef = useRef(null)

  const send = async (fullText) => {
    setBusy(true); setErr(null)
    try {
      const r = await api.post('/communications/ussd/simulator/', { sessionId: session, text: fullText })
      setScreen(r.data.text); setEnded(r.data.end); setText(fullText); setCode(r.data.service_code)
    } catch (e) { setErr(describeError(e, t).message) } finally { setBusy(false); setInput(''); setTimeout(() => inputRef.current?.focus(), 50) }
  }
  // eslint-disable-next-line react-hooks/exhaustive-deps -- start a new simulated session only when the id changes
  useEffect(() => { send('') }, [session])
  const reply = (e) => { e.preventDefault(); if (!input.trim()) return; send(text ? `${text}*${input.trim()}` : input.trim()) }
  const restart = () => { setText(''); setScreen(null); setEnded(false); setSession(newSessionId()) }

  return (
    <>
      <PageHeader title={t('ussd.title')} subtitle={t('ussd.subtitle')} />
      <div className="mb-5"><Alert tone="info">{t('ussd.anonymousNote')}</Alert></div>
      <div className="grid gap-8 lg:grid-cols-[22rem_1fr]">
        <div className="mx-auto w-full max-w-[22rem] rounded-[2.5rem] border-[10px] border-navy bg-navy p-2 shadow-xl">
          <div className="rounded-[1.8rem] bg-[#DDE5DF] p-4">
            <div className="flex justify-between text-[11px] font-semibold text-deep"><span>Demo Network</span><span>{code}</span></div>
            <div className="mt-4 min-h-[18rem] rounded-lg bg-white p-3 font-mono text-[13px] leading-snug text-ink shadow-inner" aria-live="polite">
              {busy && !screen ? <span className="text-muted">…</span> : <pre className="whitespace-pre-wrap font-mono">{screen}</pre>}
              {ended && <p className="mt-3 border-t border-line pt-2 text-[11px] text-muted">{t('ussd.sessionEnded')}</p>}
            </div>
            {!ended ? (
              <form onSubmit={reply} className="mt-3 flex gap-2">
                <label className="sr-only" htmlFor="ussd-input">{t('ussd.reply')}</label>
                <input id="ussd-input" ref={inputRef} value={input} onChange={(e) => setInput(e.target.value)} maxLength={160} autoComplete="off"
                  className="min-h-[44px] flex-1 rounded-lg border border-line bg-white px-3 font-mono focus:border-teal focus:outline-none" />
                <Button type="submit" busy={busy} variant="teal">{t('ussd.send')}</Button>
              </form>
            ) : <Button onClick={restart} className="mt-3 w-full" variant="teal">{t('ussd.dialAgain')}</Button>}
            {!ended && <button onClick={restart} className="mt-2 w-full text-center text-xs font-semibold text-deep underline">{t('ussd.cancel')}</button>}
          </div>
        </div>
        <div className="space-y-4">
          <Alert tone="bronze" title={t('ussd.sameEngineTitle')}>{t('ussd.sameEngine')}</Alert>
          <Alert tone="info" title={t('ussd.privacyTitle')}>{t('ussd.privacy')}</Alert>
          <Card className="p-5">
            <h2 className="font-semibold text-navy">{t('ussd.tryTitle')}</h2>
            <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm text-ink">
              {['try1', 'try2', 'try3', 'try4', 'try5'].map((k) => <li key={k}>{t(`ussd.${k}`)}</li>)}
            </ol>
            <p className="mt-3 text-xs text-muted">{t('ussd.history')}: <code className="font-mono">{text || '(empty)'}</code></p>
          </Card>
          {err && <Alert tone="danger">{err}</Alert>}
        </div>
      </div>
    </>
  )
}

export function SmsDashboard() {
  const { t, lang } = useI18n()
  const { data, error, loading, reload } = useApi('/communications/sms/dashboard/')
  if (loading) return <Loading />
  if (error) return <ErrorState error={error} onRetry={reload} />
  const cell = (v) => ({ value: v, suppressed: false })
  return (
    <>
      <PageHeader title={t('sms.title')} subtitle={t('sms.subtitle')} />
      <div className="mb-5">{data.provider === 'mock'
        ? <Alert tone="bronze" title={t('sms.mockTitle')}>{t('sms.mockBody')}</Alert>
        : <Alert tone="info" title={t('sms.liveTitle')}>{t('sms.liveBody')}</Alert>}</div>
      <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-6">
        <StatTile label={t('sms.submitted')} cell={cell(data.totals.submitted)} />
        <StatTile label={t('sms.delivered')} cell={cell(data.totals.delivered)} />
        <StatTile label={t('sms.failed')} cell={cell(data.totals.failed)} />
        <StatTile label={t('sms.pending')} cell={cell(data.totals.pending)} />
        <StatTile label={t('sms.simulated')} cell={cell(data.totals.simulated)} />
        <StatTile label={t('sms.blocked')} cell={cell(data.totals.blocked_no_consent)} />
      </div>
      <div className="mt-6 grid gap-6 lg:grid-cols-[18rem_1fr]">
        <Card>
          <CardHeader title={t('sms.byType')} />
          <ul className="divide-y divide-line">{data.by_type.map((r) => (
            <li key={r.notification_type} className="flex justify-between px-5 py-2.5 text-sm"><span>{t(`notifType.${r.notification_type}`)}</span><span className="font-semibold tabular-nums">{r.n}</span></li>
          ))}{data.by_type.length === 0 && <li className="px-5 py-4 text-sm text-muted">{t('sms.none')}</li>}</ul>
        </Card>
        <Card>
          <CardHeader title={t('sms.recent')} subtitle={t('sms.recentHint')} />
          {data.recent.length === 0 ? <EmptyState icon="msg" title={t('sms.none')} /> : (
            <Table head={[t('sms.when'), t('sms.recipient'), t('sms.type'), t('sms.language'), t('sms.status')]}>
              {data.recent.map((m) => (
                <tr key={m.id}>
                  <td className="whitespace-nowrap px-4 py-2.5 text-muted">{fmtDateTime(m.created_at, lang)}</td>
                  <td className="px-4 py-2.5 font-mono text-xs">{m.phone_masked || '—'}<span className="block font-sans text-muted">{m.recipient_role && t(`roles.${m.recipient_role}`)}</span></td>
                  <td className="px-4 py-2.5">{t(`notifType.${m.notification_type}`)}</td>
                  <td className="px-4 py-2.5 uppercase">{m.language}</td>
                  <td className="px-4 py-2.5"><StatusBadge status={m.delivery_status} group="smsStatus" />{m.failure_reason && <span className="block text-xs text-muted">{m.failure_reason}</span>}</td>
                </tr>
              ))}
            </Table>
          )}
        </Card>
      </div>
    </>
  )
}
