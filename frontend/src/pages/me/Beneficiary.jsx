import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { api, describeError } from '../../api/client'
import { useAuth } from '../../auth/AuthContext'
import { LanguageSelect } from '../../components/common'
import { Alert, Button, Card, EmptyState, ErrorState, Field, Icon, Input, Loading, Select, StatusBadge, Textarea } from '../../components/ui'
import { useApi } from '../../hooks/useApi'
import { useI18n } from '../../i18n'
import { fmtDate, fmtDateTime, relativeDays } from '../../lib/format'
import { JOURNEY } from '../../lib/labels'

/** Five-step "where is my case" path. Text + position + icon, never colour alone. */
export function JourneyPath({ current }) {
  const { t } = useI18n()
  const idx = Math.max(0, JOURNEY.indexOf(current))
  return (
    <ol className="grid grid-cols-6 gap-1" aria-label={t('ben.journeyLabel')}>
      {JOURNEY.map((step, i) => {
        const state = i < idx ? 'done' : i === idx ? 'now' : 'later'
        return (
          <li key={step} className="flex flex-col items-center text-center" aria-current={state === 'now' ? 'step' : undefined}>
            <span className={`flex h-9 w-9 items-center justify-center rounded-full border-2 ${state === 'done' ? 'border-success bg-success text-white' : state === 'now' ? 'border-teal bg-teal-50 text-teal ring-4 ring-teal/15' : 'border-line bg-white text-muted'}`}>
              {state === 'done' ? <Icon name="check" className="h-4 w-4" /> : <span className="text-sm font-bold">{i + 1}</span>}
            </span>
            <span className={`mt-1.5 w-full text-[10px] leading-tight [overflow-wrap:anywhere] [hyphens:auto] sm:text-xs ${state === 'now' ? 'font-bold text-navy' : 'text-muted'}`}>{t(`journey.${step}`)}</span>
            {state === 'now' && <span className="sr-only">{t('ben.youAreHere')}</span>}
          </li>
        )
      })}
    </ol>
  )
}

function NextAppointment({ appt }) {
  const { t, lang } = useI18n()
  if (!appt) return null
  const days = relativeDays(appt.scheduled_for)
  return (
    <div className="flex gap-4 rounded-xl border border-bronze/30 bg-bronze-50 p-4">
      <div className="w-16 shrink-0 self-start rounded-lg bg-white py-1.5 text-center shadow-card">
        <p className="text-[11px] font-bold uppercase text-bronze">{new Date(appt.scheduled_for).toLocaleDateString('en-GB', { month: 'short', timeZone: 'Africa/Kampala' })}</p>
        <p className="font-serif text-2xl font-semibold text-navy">{new Date(appt.scheduled_for).toLocaleDateString('en-GB', { day: 'numeric', timeZone: 'Africa/Kampala' })}</p>
      </div>
      <div className="min-w-0">
        <p className="font-semibold text-navy">{t(`benAppointment.${appt.type}`)}</p>
        <p className="text-sm text-ink">{fmtDateTime(appt.scheduled_for, lang)} · {appt.public_location}</p>
        <p className="text-sm font-semibold text-[#6b5636]">{days <= 0 ? t('ben.today') : t('ben.inDays', { n: days })}</p>
        {appt.status === 'RESCHEDULED' && <p className="text-xs text-warn-700">{t('ben.dateChanged')}</p>}
        {appt.note && <p className="mt-1 text-sm text-ink">{appt.note}</p>}
      </div>
    </div>
  )
}

export function BeneficiaryHome() {
  const { t, lang } = useI18n()
  const { user } = useAuth()
  const { data, error, loading, reload } = useApi('/beneficiary/cases/')
  return (
    <>
      <h1 className="font-serif text-2xl font-semibold text-navy">{t('ben.hello', { name: user.full_name?.split(' (')[0] || '' })}</h1>
      <p className="mt-1 text-muted">{t('ben.intro')}</p>
      <div className="mt-6 space-y-4">
        {loading ? <Loading /> : error ? <ErrorState error={error} onRetry={reload} /> : data.length === 0 ? (
          <Card><EmptyState icon="shield" title={t('ben.noCases')}>{t('ben.noCasesHint')}</EmptyState></Card>
        ) : data.map((c) => (
          <Card key={c.id} className="overflow-hidden">
            <div className="border-b border-line bg-navy px-5 py-4 text-white">
              <p className="text-xs uppercase tracking-wider text-white/60">{t('ben.yourCase')}</p>
              <p className="font-mono text-lg font-semibold">{c.reference}</p>
            </div>
            <div className="space-y-5 p-5">
              <section aria-labelledby={`q1-${c.id}`}>
                <h2 id={`q1-${c.id}`} className="mb-3 text-sm font-semibold text-muted">{t('ben.q.where')}</h2>
                <JourneyPath current={c.journey_step} />
              </section>
              {c.last_update_message && (
                <section className="rounded-xl bg-teal-50 p-4">
                  <h2 className="text-sm font-semibold text-teal-700">{t('ben.q.latest')}</h2>
                  <p className="mt-1 text-ink">{c.last_update_message}</p>
                  <p className="mt-1 text-xs text-muted">{fmtDate(c.last_update_at, lang)}</p>
                </section>
              )}
              {c.next_appointment && <section><h2 className="mb-2 text-sm font-semibold text-muted">{t('ben.q.attend')}</h2><NextAppointment appt={c.next_appointment} /></section>}
              <section>
                <h2 className="text-sm font-semibold text-muted">{t('ben.q.help')}</h2>
                <p className="mt-1 text-ink">{t('ben.officer', { name: c.support_officer.name, institution: c.support_officer.institution })}</p>
                {c.support_officer.contact && <p className="text-sm text-muted">{c.support_officer.contact}</p>}
              </section>
              <div className="flex flex-wrap gap-2 pt-1">
                <Link to={`/me/cases/${c.id}`} className="inline-flex min-h-[48px] flex-1 items-center justify-center gap-2 rounded-lg bg-navy px-4 font-semibold text-white hover:bg-deep">{t('ben.seeEverything')}<Icon name="arrowRight" className="h-4 w-4" /></Link>
                <Link to={`/me/help?case=${c.id}`} className="inline-flex min-h-[48px] flex-1 items-center justify-center gap-2 rounded-lg border border-line bg-white px-4 font-semibold text-deep hover:bg-ivory"><Icon name="help" className="h-4 w-4" />{t('ben.askHelp')}</Link>
              </div>
            </div>
          </Card>
        ))}
        <Alert tone="danger" title={t('ben.emergencyTitle')}>{t('ben.emergency')}</Alert>
      </div>
    </>
  )
}

export function BeneficiaryCase() {
  const { id } = useParams()
  const { t, lang } = useI18n()
  const summary = useApi(`/beneficiary/cases/${id}/`)
  const updates = useApi(`/beneficiary/cases/${id}/updates/`)
  const appts = useApi(`/beneficiary/cases/${id}/appointments/`)
  const services = useApi(`/beneficiary/cases/${id}/services/`)
  if (summary.loading) return <Loading />
  if (summary.error) return <ErrorState error={summary.error} />
  const c = summary.data
  const upcoming = (appts.data || []).filter((a) => new Date(a.scheduled_for) >= new Date())
  return (
    <>
      <Link to="/me" className="inline-flex items-center gap-1 text-sm font-semibold text-teal"><Icon name="arrowLeft" className="h-4 w-4" />{t('ben.nav.home')}</Link>
      <h1 className="mt-2 font-serif text-2xl font-semibold text-navy">{t('ben.yourCase')} <span className="font-mono">{c.reference}</span></h1>
      <Card className="mt-5 p-5"><h2 className="mb-3 font-semibold text-navy">{t('ben.q.where')}</h2><JourneyPath current={c.journey_step} /></Card>

      <Card className="mt-5 p-5">
        <h2 className="font-semibold text-navy">{t('ben.q.happened')}</h2>
        <p className="mb-4 text-sm text-muted">{t('ben.timelineHint')}</p>
        {updates.loading ? <Loading /> : updates.error ? <ErrorState error={updates.error} /> : updates.data.length === 0 ? <p className="text-sm text-muted">{t('ben.noUpdates')}</p> : (
          <ol className="relative ml-2 space-y-5 border-l-2 border-teal-100 pl-6">
            {[...updates.data].reverse().map((u, i) => (
              <li key={u.id} className="relative">
                <span className={`absolute -left-[33px] top-1 h-4 w-4 rounded-full border-2 border-white ${i === 0 ? 'bg-teal ring-4 ring-teal/15' : 'bg-sage'}`} />
                <p className="text-xs font-semibold text-muted">{fmtDate(u.date, lang)}{i === 0 && ` · ${t('ben.latest')}`}</p>
                <p className="mt-0.5 text-ink">{u.message}</p>
              </li>
            ))}
          </ol>
        )}
      </Card>

      <Card className="mt-5 p-5">
        <h2 className="mb-3 font-semibold text-navy">{t('ben.q.attend')}</h2>
        {appts.loading ? <Loading /> : upcoming.length === 0 ? <p className="text-sm text-muted">{t('ben.noAppointments')}</p> : <div className="space-y-3">{upcoming.map((a) => <NextAppointment key={a.id} appt={a} />)}</div>}
      </Card>

      <Card className="mt-5 p-5">
        <h2 className="mb-3 font-semibold text-navy">{t('ben.connected')}</h2>
        {services.loading ? <Loading /> : !services.data?.connected.length ? <p className="text-sm text-muted">{t('ben.noConnected')}</p> : (
          <ul className="space-y-2">{services.data.connected.map((s, i) => (
            <li key={i} className="flex items-center gap-3 rounded-lg border border-line p-3">
              <Icon name={s.status === 'COMPLETED' ? 'check' : 'heart'} className={`h-5 w-5 ${s.status === 'COMPLETED' ? 'text-success' : 'text-teal'}`} />
              <div className="min-w-0 flex-1"><p className="font-semibold text-ink">{t(`benService.${s.category}`)}</p><p className="text-sm text-muted">{s.institution}{s.contact && ` · ${s.contact}`}</p></div>
              <span className="text-xs font-semibold text-muted">{t(`benServiceStatus.${s.status}`)}</span>
            </li>
          ))}</ul>
        )}
      </Card>

      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        <Link to={`/me/help?case=${c.id}`} className="inline-flex min-h-[52px] items-center justify-center gap-2 rounded-lg bg-navy px-4 font-semibold text-white hover:bg-deep"><Icon name="help" className="h-5 w-5" />{t('ben.askHelp')}</Link>
        <Link to="/me/support" className="inline-flex min-h-[52px] items-center justify-center gap-2 rounded-lg border border-line bg-white px-4 font-semibold text-deep hover:bg-ivory"><Icon name="heart" className="h-5 w-5" />{t('ben.nav.support')}</Link>
      </div>
    </>
  )
}

export function RequestHelp() {
  const { t, lang } = useI18n()
  const [params] = useSearchParams()
  const cases = useApi('/beneficiary/cases/')
  const mine = useApi('/beneficiary/assistance-requests/')
  const [sent, setSent] = useState(false)
  const [err, setErr] = useState(null)
  const { register, handleSubmit, reset, watch, formState: { isSubmitting } } = useForm({ values: { case_id: params.get('case') || cases.data?.[0]?.id || '', request_type: 'CALL_BACK', message: '', preferred_contact_time: '' } })
  const type = watch('request_type')
  const submit = async (v) => {
    setErr(null)
    try { await api.post('/beneficiary/assistance-requests/', v); setSent(true); reset(); mine.reload() } catch (e) { setErr(describeError(e, t).message) }
  }
  if (cases.loading) return <Loading />
  return (
    <>
      <h1 className="font-serif text-2xl font-semibold text-navy">{t('help.title')}</h1>
      <p className="mt-1 text-muted">{t('help.intro')}</p>
      {cases.data?.length === 0 ? <Card className="mt-5"><EmptyState title={t('ben.noCases')}>{t('ben.noCasesHint')}</EmptyState></Card> : (
        <Card className="mt-5 p-5">
          {sent ? (
            <div className="space-y-4"><Alert tone="success" title={t('help.sentTitle')}>{t('help.sent')}</Alert><Button variant="secondary" onClick={() => setSent(false)}>{t('help.another')}</Button></div>
          ) : (
            <form onSubmit={handleSubmit(submit)} className="space-y-4">
              {cases.data?.length > 1 && <Field label={t('help.case')}>{(a) => <Select {...a} {...register('case_id')}>{cases.data.map((c) => <option key={c.id} value={c.id}>{c.reference}</option>)}</Select>}</Field>}
              <fieldset>
                <legend className="mb-2 text-sm font-semibold text-ink">{t('help.what')}</legend>
                <div className="grid gap-2 sm:grid-cols-2">
                  {['CALL_BACK', 'QUESTION', 'APPOINTMENT_HELP', 'SUPPORT_SERVICE', 'SAFETY_CONCERN', 'OTHER'].map((x) => (
                    <label key={x} className="flex min-h-[52px] cursor-pointer items-center gap-3 rounded-lg border border-line px-3 has-[:checked]:border-teal has-[:checked]:bg-teal-50">
                      <input type="radio" value={x} className="h-4 w-4 text-teal" {...register('request_type')} />
                      <span className="text-sm font-semibold text-ink">{t(`assistanceType.${x}`)}</span>
                    </label>
                  ))}
                </div>
              </fieldset>
              {type === 'SAFETY_CONCERN' && <Alert tone="danger">{t('help.safetyNow')}</Alert>}
              <Field label={t('help.message')} hint={t('help.messageHint')}>{(a) => <Textarea {...a} maxLength={500} {...register('message')} />}</Field>
              <Field label={t('help.when')} hint={t('help.whenHint')}>{(a) => <Input {...a} maxLength={100} {...register('preferred_contact_time')} />}</Field>
              {err && <Alert tone="danger">{err}</Alert>}
              <Button type="submit" size="lg" className="w-full" busy={isSubmitting}>{t('help.send')}</Button>
            </form>
          )}
        </Card>
      )}
      <h2 className="mt-8 font-semibold text-navy">{t('help.myRequests')}</h2>
      <div className="mt-3 space-y-3">
        {mine.loading ? <Loading /> : !mine.data?.length ? <p className="text-sm text-muted">{t('help.none')}</p> : mine.data.map((r) => (
          <Card key={r.id} className="p-4">
            <div className="flex flex-wrap items-center justify-between gap-2"><p className="font-semibold text-ink">{t(`assistanceType.${r.request_type}`)}</p><StatusBadge status={r.status} group="assistanceStatus" /></div>
            <p className="text-xs text-muted">{fmtDateTime(r.created_at, lang)}</p>
            {r.response_message && <p className="mt-2 rounded-lg bg-teal-50 p-3 text-sm text-ink"><span className="font-semibold">{t('help.reply')}:</span> {r.response_message}</p>}
          </Card>
        ))}
      </div>
    </>
  )
}

export function SupportServices() {
  const { t } = useI18n()
  const { data, error, loading } = useApi('/support-services/', { params: { page_size: 50 } })
  return (
    <>
      <h1 className="font-serif text-2xl font-semibold text-navy">{t('support.title')}</h1>
      <p className="mt-1 text-muted">{t('support.intro')}</p>
      <div className="mt-5"><Alert tone="danger" title={t('ben.emergencyTitle')}>{t('ben.emergency')}</Alert></div>
      <div className="mt-5 space-y-3">
        {loading ? <Loading /> : error ? <ErrorState error={error} /> : data.results.map((s) => (
          <Card key={s.id} className="p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-teal">{t(`serviceCategory.${s.category}`)}</p>
            <p className="mt-0.5 font-semibold text-navy">{s.name}</p>
            <p className="mt-1 text-sm text-ink">{s.description}</p>
            <p className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted">
              {s.public_contact && <span className="inline-flex items-center gap-1"><Icon name="phone" className="h-4 w-4" />{s.public_contact}</span>}
              {s.hours && <span className="inline-flex items-center gap-1"><Icon name="clock" className="h-4 w-4" />{s.hours}</span>}
              {s.is_free && <span className="font-semibold text-success-700">{t('support.free')}</span>}
            </p>
          </Card>
        ))}
      </div>
    </>
  )
}

export function BeneficiarySettings() {
  const { t } = useI18n()
  const { logout } = useAuth()
  return (
    <>
      <h1 className="font-serif text-2xl font-semibold text-navy">{t('ben.nav.settings')}</h1>
      <Card className="mt-5 space-y-3 p-5">
        <h2 className="font-semibold text-navy">{t('settings.languageTitle')}</h2>
        <LanguageSelect onChange={(l) => api.patch('/auth/me/', { preferred_language: l }).catch(() => {})} />
      </Card>
      <Card className="mt-5 space-y-3 p-5">
        <h2 className="font-semibold text-navy">{t('ben.safetyTitle')}</h2>
        <ul className="list-disc space-y-1.5 pl-5 text-sm text-ink">
          {['tip1', 'tip2', 'tip3', 'tip4'].map((k) => <li key={k}>{t(`ben.${k}`)}</li>)}
        </ul>
        <Button variant="secondary" onClick={() => logout()}>{t('nav.signOut')}</Button>
      </Card>
      <Card className="mt-5 p-5">
        <h2 className="font-semibold text-navy">{t('ben.messagesTitle')}</h2>
        <p className="mt-1 text-sm text-muted">{t('ben.messagesBody')}</p>
      </Card>
    </>
  )
}
