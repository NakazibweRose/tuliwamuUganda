import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, describeError } from '../../api/client'
import {
  Alert, Badge, Button, Card, CardHeader, Checkbox, Detail, EmptyState, ErrorState, Field, Icon, Input, Loading, PageHeader, Select, Table, Tabs, Textarea,
} from '../../components/ui'
import { useApi } from '../../hooks/useApi'
import { useI18n } from '../../i18n'
import { fmtDateTime } from '../../lib/format'
import { AGE_RANGES, INCIDENT_CATEGORIES, REGIONS } from '../../lib/labels'

const STATUS_TONE = { PROCESSING: 'neutral', AWAITING_VERIFICATION: 'warn', NEEDS_INFO: 'info', REGISTERED: 'success', NOT_REGISTERED: 'neutral' }

function Countdown({ c }) {
  const { t } = useI18n()
  if (!['PROCESSING', 'AWAITING_VERIFICATION', 'NEEDS_INFO'].includes(c.status)) return null
  const h = Math.round((new Date(c.respond_by).getTime() - Date.now()) / 3600000)
  if (c.is_overdue || h < 0) return <Badge tone="danger">{t('complaints.overdue')}</Badge>
  return <Badge tone={h < 6 ? 'warn' : 'neutral'} icon="clock">{t('complaints.hoursLeft', { n: h })}</Badge>
}

export function ComplaintList() {
  const { t, lang } = useI18n()
  const [status, setStatus] = useState('OPEN')
  const { data, error, loading, reload } = useApi('/complaints/', { params: { status } })
  useEffect(() => { const id = setInterval(reload, 60000); return () => clearInterval(id) }, [reload])
  return (
    <>
      <PageHeader title={t('complaints.title')} subtitle={t('complaints.subtitle')} />
      <div className="mb-5"><Alert tone="info" title={t('complaints.slaTitle')}>{t('complaints.sla')}</Alert></div>
      <Tabs value={status} onChange={setStatus} tabs={[['OPEN', t('complaints.open')], ['REGISTERED', t('complaintStatus.REGISTERED')], ['NOT_REGISTERED', t('complaintStatus.NOT_REGISTERED')], ['', t('common.all')]].map(([id, label]) => ({ id, label }))} />
      <Card>
        {loading && !data ? <Loading /> : error ? <div className="p-4"><ErrorState error={error} onRetry={reload} /></div>
          : data.results.length === 0 ? <EmptyState icon="check" title={t('complaints.empty')} /> : (
            <Table head={[t('complaints.reference'), t('complaints.received'), t('complaints.aiCategory'), t('complaints.urgency'), t('complaints.language'), t('complaints.status'), '']}>
              {data.results.map((c) => (
                <tr key={c.id} className="hover:bg-ivory/70">
                  <td className="px-4 py-3"><Link to={`/app/complaints/${c.id}`} className="font-mono font-semibold text-navy hover:underline">{c.reference}</Link>
                    {c.has_audio && <span className="ml-2 inline-flex text-teal" title={t('complaints.hasAudio')}><Icon name="phoneSim" className="h-4 w-4" /></span>}
                    {c.immediate_danger && <span className="ml-2"><Badge tone="danger">{t('complaints.dangerNow')}</Badge></span>}</td>
                  <td className="whitespace-nowrap px-4 py-3 text-muted">{fmtDateTime(c.created_at, lang)}</td>
                  <td className="px-4 py-3">{c.ai_category ? t(`incident.${c.ai_category}`) : <span className="text-muted">{t(`aiStatus.${c.ai_status}`)}</span>}</td>
                  <td className="px-4 py-3">{c.ai_urgency ? <Badge tone={c.ai_urgency === 'HIGH' ? 'danger' : c.ai_urgency === 'MEDIUM' ? 'warn' : 'neutral'}>{t(`urgency.${c.ai_urgency}`)}</Badge> : '—'}</td>
                  <td className="px-4 py-3">{t(`languages.${c.language}`)}</td>
                  <td className="px-4 py-3"><Badge tone={STATUS_TONE[c.status]}>{t(`complaintStatus.${c.status}`)}</Badge></td>
                  <td className="px-4 py-3"><Countdown c={c} /></td>
                </tr>
              ))}
            </Table>
          )}
      </Card>
    </>
  )
}

function AudioPlayer({ id }) {
  const { t } = useI18n()
  const [url, setUrl] = useState(null)
  const [busy, setBusy] = useState(false)
  useEffect(() => () => { if (url) URL.revokeObjectURL(url) }, [url])
  const load = async () => {
    setBusy(true)
    try { const r = await api.get(`/complaints/${id}/audio/`, { responseType: 'blob' }); setUrl(URL.createObjectURL(r.data)) } finally { setBusy(false) }
  }
  return url ? <audio controls autoPlay src={url} className="w-full" /> : <Button variant="secondary" icon="phoneSim" busy={busy} onClick={load}>{t('complaints.playAudio')}</Button>
}

export function ComplaintDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { t, lang } = useI18n()
  const { data: c, error, loading, reload, setData } = useApi(`/complaints/${id}/`)
  const [panel, setPanel] = useState('register')
  const [msg, setMsg] = useState({ text: '', needs_info: true })
  const [reg, setReg] = useState(null)
  const [dec, setDec] = useState({ message: '', internal_note: '' })
  const [err, setErr] = useState(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (c && !reg) setReg({
      child_pseudonym: `Child in report ${c.reference}`, age_range: c.child_age_range, incident_category: c.ai_category || 'OTHER',
      district: c.district, region: c.region || 'CENTRAL', protection_concerns: (c.ai_summary || '').slice(0, 1000), immediate_risk: c.immediate_danger || c.ai_urgency === 'HIGH',
      allow_complainant_to_follow: c.can_follow_possible, internal_note: '',
    })
  }, [c, reg])

  if (loading) return <Loading />
  if (error) return <ErrorState error={error} onRetry={reload} />
  const open = ['PROCESSING', 'AWAITING_VERIFICATION', 'NEEDS_INFO'].includes(c.status)

  const act = async (path, body) => {
    setBusy(true); setErr(null)
    try { const r = await api.post(`/complaints/${c.id}/${path}/`, body, { timeout: 300000 }); setData(r.data); return r.data }
    catch (e) { const d = describeError(e, t); setErr(Object.entries(d.fields).map(([k, v]) => `${k}: ${v}`).join(' ') || d.message) }
    finally { setBusy(false) }
  }

  return (
    <>
      <PageHeader back={<Link to="/app/complaints" className="mb-2 inline-flex items-center gap-1 text-sm font-semibold text-teal"><Icon name="arrowLeft" className="h-4 w-4" />{t('nav.complaints')}</Link>}
        title={<span className="font-mono">{c.reference}</span>}
        subtitle={`${t(`concerning.${c.concerning}`)} · ${t(`age.${c.child_age_range}`)} · ${c.district} · ${t('complaints.from')} ${c.complainant.name}`} />
      <div className="mb-5 flex flex-wrap gap-2">
        <Badge tone={STATUS_TONE[c.status]}>{t(`complaintStatus.${c.status}`)}</Badge><Countdown c={c} />
        {c.immediate_danger && <Badge tone="danger">{t('complaints.dangerNow')}</Badge>}
        <Badge tone="neutral" icon="globe">{t('complaints.spoke', { language: t(`languages.${c.language}`) })} · {t('complaints.replyIn', { language: t(`languages.${c.reply_language}`) })}</Badge>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_24rem]">
        <div className="space-y-6">
          <Card>
            <CardHeader title={t('complaints.aiTitle')} subtitle={t('complaints.aiSubtitle')}
              action={c.ai_consent && <Button size="sm" variant="secondary" busy={busy && panel === 'ai'} onClick={() => { setPanel('ai'); act('rerun-ai', {}) }}>{c.ai_status === 'DONE' ? t('complaints.rerunAi') : t('complaints.runAi')}</Button>} />
            <div className="space-y-4 p-5">
              {c.ai_status === 'DONE' ? (
                <>
                  <div className="flex flex-wrap gap-2">
                    <Badge tone="info" icon={null}>{t(`incident.${c.ai_category}`)}</Badge>
                    <Badge tone={c.ai_urgency === 'HIGH' ? 'danger' : 'warn'}>{t('complaints.urgency')}: {t(`urgency.${c.ai_urgency}`)}</Badge>
                  </div>
                  {c.ai_summary ? <p className="text-ink">{c.ai_summary}</p> : <p className="text-sm text-muted">{t('complaints.noSummary')}</p>}
                  {c.ai_key_facts.length > 0 && <ul className="list-disc space-y-1 pl-5 text-sm text-ink">{c.ai_key_facts.map((f, i) => <li key={i}>{f}</li>)}</ul>}
                  <p className="text-xs text-muted">{t('complaints.aiModel', { model: c.ai_model, date: fmtDateTime(c.ai_processed_at, lang) })}</p>
                </>
              ) : (
                <Alert tone={c.ai_status === 'FAILED' ? 'warn' : 'info'} title={t(`aiStatus.${c.ai_status}`)}>
                  {c.ai_status === 'PROCESSING' || c.ai_status === 'PENDING' ? t('complaints.aiRunning') : c.ai_consent ? t('complaints.aiFailedHint', { reason: c.ai_error || '—' }) : t('complaints.noConsent')}
                  {c.ai_category && <span className="mt-1 block">{t('complaints.keywordGuess', { category: t(`incident.${c.ai_category}`) })}</span>}
                </Alert>
              )}
              <Alert tone="bronze">{t('complaints.aiWarning')}</Alert>
            </div>
          </Card>

          <Card>
            <CardHeader title={t('complaints.statement')} />
            <div className="space-y-5 p-5">
              {c.audio && <div><p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">{t('complaints.voiceNote')}{c.audio.duration_seconds ? ` · ${c.audio.duration_seconds}s` : ''}</p><AudioPlayer id={c.id} /><p className="mt-1 text-xs text-muted">{t('complaints.audioAudited')}</p></div>}
              {c.english_text && <Detail label={t('complaints.english')}><span className="whitespace-pre-wrap">{c.english_text}</span></Detail>}
              {c.transcript && <Detail label={t('complaints.transcript', { language: t(`languages.${c.language}`) })}><span className="whitespace-pre-wrap">{c.transcript}</span></Detail>}
              {c.written_statement && <Detail label={t('complaints.written')}><span className="whitespace-pre-wrap">{c.written_statement}</span></Detail>}
            </div>
          </Card>

          <Card>
            <CardHeader title={t('complaints.conversation')} subtitle={t('complaints.conversationHint')} />
            <ol className="space-y-3 p-5">
              {c.messages.length === 0 && <li className="text-sm text-muted">{t('report.noMessages')}</li>}
              {c.messages.map((m) => (
                <li key={m.id} className={`flex ${m.from_police ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm ${m.from_police ? 'bg-navy text-white' : 'bg-ivory text-ink'}`}>
                    <p className={`mb-1 text-xs font-semibold ${m.from_police ? 'text-white/70' : 'text-teal-700'}`}>{m.author} · {fmtDateTime(m.created_at, lang)}</p>
                    <p className="whitespace-pre-wrap">{m.from_police ? m.text : (m.translated_text || m.text)}</p>
                    {m.translated_text && <p className={`mt-2 border-t pt-2 text-xs ${m.from_police ? 'border-white/20 text-white/70' : 'border-line text-muted'}`}>
                      {m.from_police ? t('complaints.sentAs', { language: t(`languages.${m.translated_language}`) }) : t('complaints.original', { language: t(`languages.${m.text_language}`) })}: {m.from_police ? m.translated_text : m.text}
                      {m.machine_translated && ` (${t('complaints.machine')})`}</p>}
                  </div>
                </li>
              ))}
            </ol>
          </Card>
        </div>

        <div className="space-y-6">
          {c.case && (
            <Card className="p-5">
              <p className="text-sm text-muted">{t('complaints.registeredAs')}</p>
              <Link to={`/app/cases/${c.case.id}`} className="font-mono text-lg font-semibold text-teal hover:underline">{c.case.reference}</Link>
              <p className="mt-1 text-sm text-muted">{c.complainant_can_follow_case ? t('complaints.complainantFollows') : t('complaints.complainantNotFollowing')}</p>
            </Card>
          )}
          {open && reg && (
            <Card className="p-5">
              <div className="mb-4 grid grid-cols-3 gap-1 rounded-xl bg-ivory p-1">
                {[['register', t('complaints.register')], ['message', t('complaints.ask')], ['decline', t('complaints.decline')]].map(([k, label]) => (
                  <button key={k} onClick={() => { setPanel(k); setErr(null) }} className={`min-h-[40px] rounded-lg text-xs font-semibold sm:text-sm ${panel === k ? 'bg-white text-navy shadow-card' : 'text-muted'}`}>{label}</button>
                ))}
              </div>
              {panel === 'register' && (
                <div className="space-y-3">
                  <p className="text-sm text-muted">{t('complaints.registerHint')}</p>
                  <Field label={t('caseNew.pseudonym')}>{(a) => <Input {...a} value={reg.child_pseudonym} onChange={(e) => setReg({ ...reg, child_pseudonym: e.target.value })} />}</Field>
                  <div className="grid grid-cols-2 gap-3">
                    <Field label={t('caseNew.ageRange')}>{(a) => <Select {...a} value={reg.age_range} onChange={(e) => setReg({ ...reg, age_range: e.target.value })}>{AGE_RANGES.map((x) => <option key={x} value={x}>{t(`age.${x}`)}</option>)}</Select>}</Field>
                    <Field label={t('caseNew.region')}>{(a) => <Select {...a} value={reg.region} onChange={(e) => setReg({ ...reg, region: e.target.value })}>{REGIONS.map((x) => <option key={x} value={x}>{t(`region.${x}`)}</option>)}</Select>}</Field>
                  </div>
                  <Field label={t('caseNew.category')} hint={t('complaints.confirmCategory')}>{(a) => <Select {...a} value={reg.incident_category} onChange={(e) => setReg({ ...reg, incident_category: e.target.value })}>{INCIDENT_CATEGORIES.map((x) => <option key={x} value={x}>{t(`incident.${x}`)}</option>)}</Select>}</Field>
                  <Field label={t('caseNew.district')}>{(a) => <Input {...a} value={reg.district} onChange={(e) => setReg({ ...reg, district: e.target.value })} />}</Field>
                  <Field label={t('caseNew.protectionConcerns')} hint={t('complaints.concernsHint')}>{(a) => <Textarea {...a} rows={4} maxLength={1000} value={reg.protection_concerns} onChange={(e) => setReg({ ...reg, protection_concerns: e.target.value })} />}</Field>
                  <Checkbox label={t('caseNew.immediateRisk')} checked={reg.immediate_risk} onChange={(e) => setReg({ ...reg, immediate_risk: e.target.checked })} />
                  <Checkbox label={t('complaints.allowFollow')} hint={c.can_follow_possible ? t('complaints.allowFollowHint') : t('complaints.followNotPossible')}
                    disabled={!c.can_follow_possible} checked={reg.allow_complainant_to_follow && c.can_follow_possible} onChange={(e) => setReg({ ...reg, allow_complainant_to_follow: e.target.checked })} />
                  <Field label={t('complaints.internalNote')}>{(a) => <Textarea {...a} rows={2} value={reg.internal_note} onChange={(e) => setReg({ ...reg, internal_note: e.target.value })} />}</Field>
                  <Button variant="teal" className="w-full" busy={busy} onClick={async () => { const d = await act('register', reg); if (d?.case) navigate(`/app/cases/${d.case.id}?created=1`) }}>{t('complaints.registerSubmit')}</Button>
                </div>
              )}
              {panel === 'message' && (
                <div className="space-y-3">
                  <Field label={t('complaints.messageLabel')} hint={t('complaints.messageHint', { language: t(`languages.${c.reply_language}`) })}>{(a) => <Textarea {...a} rows={4} maxLength={2000} value={msg.text} onChange={(e) => setMsg({ ...msg, text: e.target.value })} />}</Field>
                  <Checkbox label={t('complaints.needsInfo')} checked={msg.needs_info} onChange={(e) => setMsg({ ...msg, needs_info: e.target.checked })} />
                  <Button className="w-full" icon="send" busy={busy} disabled={!msg.text.trim()} onClick={async () => { if (await act('message', msg)) setMsg({ text: '', needs_info: true }) }}>{t('complaints.sendMessage')}</Button>
                </div>
              )}
              {panel === 'decline' && (
                <div className="space-y-3">
                  <p className="text-sm text-muted">{t('complaints.declineHint')}</p>
                  <Field label={t('complaints.declineMessage')}>{(a) => <Textarea {...a} rows={4} value={dec.message} onChange={(e) => setDec({ ...dec, message: e.target.value })} />}</Field>
                  <Field label={t('complaints.internalNote')}>{(a) => <Textarea {...a} rows={2} value={dec.internal_note} onChange={(e) => setDec({ ...dec, internal_note: e.target.value })} />}</Field>
                  <Button variant="danger" className="w-full" busy={busy} disabled={!dec.message.trim()} onClick={() => act('decline', dec)}>{t('complaints.declineSubmit')}</Button>
                </div>
              )}
              {err && <div className="mt-3"><Alert tone="danger">{err}</Alert></div>}
            </Card>
          )}
          <Card>
            <CardHeader title={t('complaints.history')} />
            <ol className="space-y-2 p-5 text-sm">
              {c.events.map((e, i) => <li key={i}><p className="font-semibold text-ink">{e.action.replaceAll('_', ' ').toLowerCase()}</p><p className="text-xs text-muted">{fmtDateTime(e.created_at, lang)} · {e.actor}{e.note && ` · ${e.note}`}</p></li>)}
            </ol>
          </Card>
        </div>
      </div>
    </>
  )
}
