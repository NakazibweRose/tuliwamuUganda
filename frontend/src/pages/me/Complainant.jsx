import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, describeError } from '../../api/client'
import { useAuth } from '../../auth/AuthContext'
import VoiceRecorder from '../../components/VoiceRecorder'
import { Alert, Button, Card, ErrorState, Field, Icon, Input, Loading, Select, Textarea } from '../../components/ui'
import { useApi } from '../../hooks/useApi'
import { useI18n } from '../../i18n'
import { fmtDateTime } from '../../lib/format'
import { CaseCard } from './Beneficiary'

const OPEN = ['PROCESSING', 'AWAITING_VERIFICATION', 'NEEDS_INFO']
const PRIORITY_LANGS = ['lg', 'ach', 'en']
const MORE_LANGS = ['nyn', 'teo', 'sw']
const AGES = ['0-4', '5-8', '9-11', '12-14', '15-17', 'UNKNOWN']

/** Re-fetch every `ms` while the page is visible so the dashboard stays live. */
function usePolling(reload, ms = 45000) {
  useEffect(() => {
    const id = setInterval(() => { if (document.visibilityState === 'visible') reload() }, ms)
    return () => clearInterval(id)
  }, [reload, ms])
}

function hoursLeft(iso) {
  return Math.max(0, Math.round((new Date(iso).getTime() - Date.now()) / 3600000))
}

/* ------------------------------------------------------------------ Welcome */
function Illustration() {
  return (
    <svg viewBox="0 0 320 200" className="h-auto w-full max-w-sm" aria-hidden="true">
      <circle cx="250" cy="52" r="30" fill="#AD9063" opacity="0.25" />
      <circle cx="250" cy="52" r="18" fill="#AD9063" opacity="0.55" />
      <path d="M20 170c40-30 80-40 140-34s100 4 140-20v84H20z" fill="#81968B" opacity="0.25" />
      <path d="M160 44c-18 15-34 18-46 18v30c0 28 18 44 46 52 28-8 46-24 46-52V62c-12 0-28-3-46-18z" fill="#F6F5F0" stroke="#477A78" strokeWidth="5" strokeLinejoin="round" />
      <circle cx="146" cy="88" r="9" fill="#29465B" />
      <path d="M131 116c2-10 8-15 15-15s13 5 15 15" fill="none" stroke="#29465B" strokeWidth="7" strokeLinecap="round" />
      <circle cx="176" cy="96" r="7" fill="#477A78" />
      <path d="M165 118c2-7 6-11 11-11s9 4 11 11" fill="none" stroke="#477A78" strokeWidth="6" strokeLinecap="round" />
      <path d="M60 150c10-6 18-6 26 0M230 140c10-6 18-6 26 0" stroke="#477A78" strokeWidth="3" fill="none" strokeLinecap="round" opacity="0.6" />
    </svg>
  )
}

function Welcome({ name }) {
  const { t, lang, setLang } = useI18n()
  const steps = [
    { icon: 'msg', title: t('welcome.step1Title'), body: t('welcome.step1Body') },
    { icon: 'shield', title: t('welcome.step2Title'), body: t('welcome.step2Body') },
    { icon: 'heart', title: t('welcome.step3Title'), body: t('welcome.step3Body') },
  ]
  return (
    <div className="space-y-6">
      <section className="overflow-hidden rounded-3xl bg-gradient-to-br from-navy to-deep text-white shadow-card">
        <div className="grid items-center gap-4 p-6 sm:grid-cols-[1.2fr_1fr] sm:p-8">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wider text-bronze">{t('welcome.kicker')}</p>
            <h1 className="mt-2 font-serif text-3xl font-semibold leading-tight">{t('welcome.title', { name })}</h1>
            <p className="mt-3 text-white/80">{t('welcome.body')}</p>
            <Link to="/me/help" className="mt-6 inline-flex min-h-[52px] items-center gap-2 rounded-xl bg-bronze px-5 text-lg font-semibold text-white shadow hover:bg-[#9a7f55]">
              <Icon name="msg" className="h-5 w-5" />{t('welcome.cta')}
            </Link>
            <p className="mt-3 text-sm text-white/70">{t('welcome.ctaHint')}</p>
          </div>
          <div className="flex justify-center rounded-2xl bg-white/95 p-3"><Illustration /></div>
        </div>
      </section>

      <section aria-labelledby="lang-title" className="rounded-2xl border border-line bg-white p-4">
        <p id="lang-title" className="text-sm font-semibold text-ink">{t('welcome.chooseLanguage')}</p>
        <div className="mt-2 flex flex-wrap gap-2">
          {PRIORITY_LANGS.map((l) => (
            <button key={l} onClick={() => { setLang(l); api.patch('/auth/me/', { preferred_language: l }).catch(() => {}) }}
              aria-pressed={lang === l}
              className={`min-h-[44px] rounded-full border px-4 text-sm font-semibold ${lang === l ? 'border-teal bg-teal text-white' : 'border-line bg-white text-ink hover:border-teal'}`}>
              {t(`languages.${l}`)}
            </button>
          ))}
        </div>
      </section>

      <section>
        <h2 className="font-serif text-xl font-semibold text-navy">{t('welcome.howTitle')}</h2>
        <ol className="mt-3 grid gap-3 sm:grid-cols-3">
          {steps.map((s, i) => (
            <li key={s.title} className="relative rounded-2xl border border-line bg-white p-4 shadow-card">
              <span className="absolute right-4 top-4 font-serif text-2xl font-semibold text-line">{i + 1}</span>
              <span className="inline-flex rounded-xl bg-teal-50 p-2.5 text-teal"><Icon name={s.icon} /></span>
              <p className="mt-3 font-semibold text-navy">{s.title}</p>
              <p className="mt-1 text-sm text-muted">{s.body}</p>
            </li>
          ))}
        </ol>
      </section>

      <div className="grid gap-3 sm:grid-cols-2">
        <Card className="p-5">
          <p className="flex items-center gap-2 font-semibold text-navy"><Icon name="shield" className="h-5 w-5 text-bronze" />{t('welcome.privacyTitle')}</p>
          <ul className="mt-2 space-y-1.5 text-sm text-ink">
            {['privacy1', 'privacy2', 'privacy3'].map((k) => <li key={k} className="flex gap-2"><Icon name="check" className="mt-0.5 h-4 w-4 shrink-0 text-success" />{t(`welcome.${k}`)}</li>)}
          </ul>
        </Card>
        <Alert tone="danger" title={t('ben.emergencyTitle')}>{t('ben.emergency')}</Alert>
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------ Report status */
const STEPS = ['SENT', 'REVIEW', 'DECISION']

function ReportProgress({ status }) {
  const { t } = useI18n()
  const idx = status === 'PROCESSING' || status === 'AWAITING_VERIFICATION' || status === 'NEEDS_INFO' ? 1 : 2
  return (
    <ol className="grid grid-cols-3 gap-2" aria-label={t('report.progressLabel')}>
      {STEPS.map((s, i) => {
        const done = i < idx
        const now = i === idx
        return (
          <li key={s} className="text-center" aria-current={now ? 'step' : undefined}>
            <span className={`mx-auto flex h-9 w-9 items-center justify-center rounded-full border-2 ${done ? 'border-success bg-success text-white' : now ? 'border-teal bg-teal-50 text-teal ring-4 ring-teal/15' : 'border-line bg-white text-muted'}`}>
              {done ? <Icon name="check" className="h-4 w-4" /> : <span className="text-sm font-bold">{i + 1}</span>}
            </span>
            <span className={`mt-1.5 block text-xs leading-tight ${now ? 'font-bold text-navy' : 'text-muted'}`}>{t(`report.step.${s}`)}</span>
          </li>
        )
      })}
    </ol>
  )
}

function StatusMessage({ r }) {
  const { t } = useI18n()
  if (OPEN.includes(r.status) && r.status !== 'NEEDS_INFO') {
    const h = hoursLeft(r.respond_by)
    return (
      <div className="rounded-xl bg-teal-50 p-4">
        <p className="font-semibold text-teal-700">{t('report.waitTitle')}</p>
        <p className="mt-1 text-sm text-ink">{t('report.waitBody', { language: t(`languages.${r.reply_language}`) })}</p>
        <p className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-white px-3 py-1 text-xs font-semibold text-navy">
          <Icon name="clock" className="h-3.5 w-3.5" />{h > 0 ? t('report.hoursLeft', { n: h }) : t('report.anyMoment')}
        </p>
      </div>
    )
  }
  if (r.status === 'NEEDS_INFO') return <Alert tone="warn" title={t('report.needsInfoTitle')}>{t('report.needsInfoBody')}</Alert>
  if (r.status === 'REGISTERED') return <Alert tone="success" title={t('report.registeredTitle')}>{r.case ? t('report.registeredFollow') : t('report.registeredNoFollow')}</Alert>
  return <Alert tone="info" title={t('report.notRegisteredTitle')}>{t('report.notRegisteredBody')}</Alert>
}

function ReportCard({ r }) {
  const { t, lang } = useI18n()
  return (
    <Card className="p-5">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-muted">{t('report.yourReport')}</p>
          <p className="font-mono text-lg font-semibold text-navy">{r.reference}</p>
          <p className="text-xs text-muted">{t('report.sentOn', { date: fmtDateTime(r.created_at, lang) })}</p>
        </div>
        {r.unread_messages > 0 && <span className="inline-flex items-center gap-1 rounded-full bg-bronze px-3 py-1 text-xs font-bold text-white"><Icon name="msg" className="h-3.5 w-3.5" />{t('report.newMessages', { n: r.unread_messages })}</span>}
      </div>
      <div className="mt-4"><ReportProgress status={r.status} /></div>
      <div className="mt-4"><StatusMessage r={r} /></div>
      <Link to={`/me/reports/${r.id}`} className="mt-4 inline-flex min-h-[48px] w-full items-center justify-center gap-2 rounded-lg border border-line bg-white px-4 font-semibold text-deep hover:bg-ivory">
        {r.status === 'NEEDS_INFO' ? t('report.answerPolice') : t('report.openReport')}<Icon name="arrowRight" className="h-4 w-4" />
      </Link>
    </Card>
  )
}

/* ------------------------------------------------------------------ Home */
export function ComplainantHome() {
  const { t } = useI18n()
  const { user } = useAuth()
  const reports = useApi('/my/reports/')
  const cases = useApi('/beneficiary/cases/')
  const reload = useMemo(() => () => { reports.reload(); cases.reload() }, [reports.reload, cases.reload]) // eslint-disable-line react-hooks/exhaustive-deps
  usePolling(reload)
  const firstName = (user.full_name || '').split(' (')[0]

  if (reports.loading || cases.loading) return <Loading />
  if (reports.error || cases.error) return <ErrorState error={reports.error || cases.error} onRetry={reload} />
  const openReports = reports.data.filter((r) => OPEN.includes(r.status) || (r.status !== 'REGISTERED' && r.unread_messages))
  const decided = reports.data.filter((r) => !openReports.includes(r) && !(r.case && cases.data.some((c) => c.id === r.case.id)))

  if (reports.data.length === 0 && cases.data.length === 0) return <Welcome name={firstName} />

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-serif text-2xl font-semibold text-navy">{t('ben.hello', { name: firstName })}</h1>
          <p className="mt-1 text-muted">{t('dashboard.intro')}</p>
        </div>
        <Link to="/me/help" className="inline-flex min-h-[44px] items-center gap-2 rounded-lg bg-navy px-4 font-semibold text-white hover:bg-deep"><Icon name="plus" className="h-4 w-4" />{t('dashboard.newReport')}</Link>
      </div>

      {openReports.length > 0 && (
        <section className="space-y-3" aria-labelledby="open-reports">
          <h2 id="open-reports" className="text-sm font-semibold uppercase tracking-wider text-muted">{t('dashboard.reportsInReview')}</h2>
          {openReports.map((r) => <ReportCard key={r.id} r={r} />)}
        </section>
      )}

      {cases.data.length > 0 && (
        <section className="space-y-3" aria-labelledby="my-cases">
          <h2 id="my-cases" className="text-sm font-semibold uppercase tracking-wider text-muted">{t('dashboard.myCases')}</h2>
          {cases.data.map((c) => <CaseCard key={c.id} c={c} />)}
        </section>
      )}

      {decided.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-muted">{t('dashboard.earlierReports')}</h2>
          {decided.map((r) => <ReportCard key={r.id} r={r} />)}
        </section>
      )}
      <Alert tone="danger" title={t('ben.emergencyTitle')}>{t('ben.emergency')}</Alert>
    </div>
  )
}

/* ------------------------------------------------------------------ Report wizard (Get help) */
function Choice({ selected, onClick, icon, title, hint }) {
  return (
    <button type="button" onClick={onClick} aria-pressed={selected}
      className={`flex min-h-[64px] w-full items-center gap-3 rounded-xl border-2 p-3 text-left transition ${selected ? 'border-teal bg-teal-50' : 'border-line bg-white hover:border-teal/50'}`}>
      <span className={`rounded-lg p-2 ${selected ? 'bg-teal text-white' : 'bg-ivory text-teal'}`}><Icon name={icon} /></span>
      <span><span className="block font-semibold text-navy">{title}</span>{hint && <span className="block text-xs text-muted">{hint}</span>}</span>
    </button>
  )
}

export function ReportWizard() {
  const { t, lang } = useI18n()
  const navigate = useNavigate()
  const [step, setStep] = useState(0)
  const [mode, setMode] = useState('voice')
  const [voice, setVoice] = useState(null)
  const [form, setForm] = useState({
    concerning: '', child_age_range: '', district: '', immediate_danger: null,
    language: PRIORITY_LANGS.includes(lang) ? lang : 'en', reply_language: '', written_statement: '', ai_consent: true,
  })
  const [err, setErr] = useState(null)
  const [busy, setBusy] = useState(false)
  const [progress, setProgress] = useState(0)
  const [done, setDone] = useState(null)
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }))
  const replyLang = form.reply_language || form.language

  const canNext = [
    form.concerning && form.child_age_range && form.district.trim().length >= 2 && form.immediate_danger !== null,
    voice || form.written_statement.trim().length >= 10,
    true,
  ][step]

  async function submit() {
    setBusy(true); setErr(null); setProgress(0)
    const fd = new FormData()
    Object.entries({ ...form, reply_language: replyLang }).forEach(([k, v]) => fd.append(k, String(v)))
    if (voice) {
      const ext = voice.type.includes('mp4') ? 'm4a' : voice.type.includes('ogg') ? 'ogg' : voice.type.includes('mpeg') ? 'mp3' : 'webm'
      fd.append('audio', new File([voice.blob], `voice-note.${ext}`, { type: voice.type }))
      if (voice.seconds) fd.append('audio_seconds', String(voice.seconds))
    }
    try {
      const r = await api.post('/my/reports/', fd, { timeout: 120000, onUploadProgress: (e) => e.total && setProgress(Math.round((e.loaded / e.total) * 100)) })
      if (voice?.url) URL.revokeObjectURL(voice.url)
      setDone(r.data)
    } catch (e) {
      const d = describeError(e, t)
      setErr(Object.values(d.fields)[0] || d.message)
    } finally { setBusy(false) }
  }

  if (done) {
    return (
      <Card className="mx-auto max-w-xl p-6 text-center sm:p-8">
        <span className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-success text-white"><Icon name="check" className="h-8 w-8" /></span>
        <h1 className="mt-4 font-serif text-2xl font-semibold text-navy">{t('report.thanksTitle')}</h1>
        <p className="mt-2 text-ink">{t('report.thanksBody', { language: t(`languages.${done.reply_language}`) })}</p>
        <p className="mt-4 rounded-xl bg-ivory px-4 py-3 text-sm text-muted">{t('report.referenceLabel')} <span className="font-mono text-base font-semibold text-navy">{done.reference}</span></p>
        <p className="mt-3 inline-flex items-center gap-1.5 text-sm font-semibold text-teal-700"><Icon name="clock" className="h-4 w-4" />{t('report.answerBy', { date: fmtDateTime(done.respond_by, lang) })}</p>
        <div className="mt-6 grid gap-2 sm:grid-cols-2">
          <Button onClick={() => navigate('/me')}>{t('report.toDashboard')}</Button>
          <Button variant="secondary" onClick={() => navigate('/me/settings')}>{t('report.safetyTips')}</Button>
        </div>
      </Card>
    )
  }

  const stepTitles = [t('report.s1Title'), t('report.s2Title'), t('report.s3Title')]
  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="font-serif text-2xl font-semibold text-navy">{t('report.title')}</h1>
      <p className="mt-1 text-muted">{t('report.intro')}</p>
      <div className="mt-5 flex gap-1.5" aria-hidden="true">{stepTitles.map((_, i) => <span key={i} className={`h-1.5 flex-1 rounded-full ${i <= step ? 'bg-teal' : 'bg-line'}`} />)}</div>
      <p className="mt-2 text-sm font-semibold text-teal-700">{t('report.stepOf', { n: step + 1, total: 3 })} · {stepTitles[step]}</p>

      <Card className="mt-4 space-y-5 p-5">
        {step === 0 && (
          <>
            <fieldset>
              <legend className="mb-2 font-semibold text-navy">{t('report.whoAbout')}</legend>
              <div className="grid gap-2 sm:grid-cols-2">
                {[['SELF', 'users'], ['MY_CHILD', 'heart'], ['CHILD_IN_CARE', 'home'], ['OTHER_CHILD', 'eye']].map(([k, ic]) => (
                  <Choice key={k} icon={ic} selected={form.concerning === k} onClick={() => set('concerning', k)} title={t(`concerning.${k}`)} hint={k === 'OTHER_CHILD' ? t('report.otherChildHint') : null} />
                ))}
              </div>
            </fieldset>
            <fieldset>
              <legend className="mb-2 font-semibold text-navy">{t('report.childAge')}</legend>
              <div className="flex flex-wrap gap-2">
                {AGES.map((a) => (
                  <button key={a} type="button" aria-pressed={form.child_age_range === a} onClick={() => set('child_age_range', a)}
                    className={`min-h-[44px] rounded-full border px-4 text-sm font-semibold ${form.child_age_range === a ? 'border-teal bg-teal text-white' : 'border-line bg-white text-ink'}`}>{t(`age.${a}`)}</button>
                ))}
              </div>
            </fieldset>
            <Field label={t('report.district')} hint={t('report.districtHint')}>{(a) => <Input {...a} value={form.district} onChange={(e) => set('district', e.target.value)} autoComplete="off" />}</Field>
            <fieldset>
              <legend className="mb-2 font-semibold text-navy">{t('report.dangerNow')}</legend>
              <div className="grid grid-cols-2 gap-2">
                <Choice icon="alert" selected={form.immediate_danger === true} onClick={() => set('immediate_danger', true)} title={t('common.yes')} />
                <Choice icon="check" selected={form.immediate_danger === false} onClick={() => set('immediate_danger', false)} title={t('report.noOrNotSure')} />
              </div>
              {form.immediate_danger && <div className="mt-3"><Alert tone="danger" title={t('report.callNowTitle')}>{t('report.callNow')}</Alert></div>}
            </fieldset>
          </>
        )}

        {step === 1 && (
          <>
            <fieldset>
              <legend className="mb-2 font-semibold text-navy">{t('report.whichLanguage')}</legend>
              <div className="flex flex-wrap gap-2">
                {[...PRIORITY_LANGS, ...MORE_LANGS].map((l) => (
                  <button key={l} type="button" aria-pressed={form.language === l} onClick={() => set('language', l)}
                    className={`min-h-[44px] rounded-full border px-4 text-sm font-semibold ${form.language === l ? 'border-teal bg-teal text-white' : PRIORITY_LANGS.includes(l) ? 'border-line bg-white text-ink' : 'border-dashed border-line bg-white text-muted'}`}>{t(`languages.${l}`)}</button>
                ))}
              </div>
            </fieldset>
            <div className="grid grid-cols-2 gap-1 rounded-xl bg-ivory p-1" role="tablist">
              {[['voice', 'phoneSim', t('report.speak')], ['text', 'file', t('report.write')]].map(([m, ic, label]) => (
                <button key={m} type="button" role="tab" aria-selected={mode === m} onClick={() => setMode(m)}
                  className={`inline-flex min-h-[44px] items-center justify-center gap-2 rounded-lg text-sm font-semibold ${mode === m ? 'bg-white text-navy shadow-card' : 'text-muted'}`}>
                  <Icon name={ic} className="h-4 w-4" />{label}{(m === 'voice' ? voice : form.written_statement) && <Icon name="check" className="h-4 w-4 text-success" />}
                </button>
              ))}
            </div>
            <div className="rounded-xl bg-teal-50 p-4 text-sm text-ink">
              <p className="font-semibold text-teal-700">{t('report.promptTitle')}</p>
              <ul className="mt-1 list-disc space-y-0.5 pl-5">{['p1', 'p2', 'p3', 'p4'].map((k) => <li key={k}>{t(`report.${k}`)}</li>)}</ul>
            </div>
            {mode === 'voice'
              ? <VoiceRecorder value={voice} onChange={setVoice} />
              : <Field label={t('report.writeLabel')} hint={t('report.writeHint')}>{(a) => <Textarea {...a} rows={7} maxLength={5000} value={form.written_statement} onChange={(e) => set('written_statement', e.target.value)} />}</Field>}
            <p className="text-xs text-muted">{t('report.bothOk')}</p>
          </>
        )}

        {step === 2 && (
          <>
            <Field label={t('report.replyLanguage')} hint={t('report.replyLanguageHint')}>
              {(a) => <Select {...a} value={replyLang} onChange={(e) => set('reply_language', e.target.value)}>
                {[...PRIORITY_LANGS, ...MORE_LANGS].map((l) => <option key={l} value={l}>{t(`languages.${l}`)}</option>)}
              </Select>}
            </Field>
            <div className="rounded-xl border border-line p-4">
              <label className="flex items-start gap-3">
                <input type="checkbox" className="mt-1 h-5 w-5 rounded border-line text-teal" checked={form.ai_consent} onChange={(e) => set('ai_consent', e.target.checked)} />
                <span>
                  <span className="block font-semibold text-navy">{t('report.aiConsent')}</span>
                  <span className="mt-1 block text-sm text-muted">{t('report.aiConsentHint')}</span>
                </span>
              </label>
            </div>
            <div className="rounded-xl bg-ivory p-4">
              <p className="font-semibold text-navy">{t('report.reviewTitle')}</p>
              <dl className="mt-2 grid grid-cols-2 gap-2 text-sm">
                <dt className="text-muted">{t('report.whoAbout')}</dt><dd>{t(`concerning.${form.concerning}`)}</dd>
                <dt className="text-muted">{t('report.childAge')}</dt><dd>{t(`age.${form.child_age_range}`)}</dd>
                <dt className="text-muted">{t('report.district')}</dt><dd>{form.district}</dd>
                <dt className="text-muted">{t('report.yourStory')}</dt><dd>{[voice && t('report.voiceNote'), form.written_statement && t('report.writtenStatement')].filter(Boolean).join(' + ')}</dd>
              </dl>
            </div>
            <Alert tone="info" title={t('report.whatNextTitle')}>{t('report.whatNext', { language: t(`languages.${replyLang}`) })}</Alert>
          </>
        )}

        {err && <Alert tone="danger">{err}</Alert>}
        {busy && progress > 0 && progress < 100 && <p className="text-sm text-muted" aria-live="polite">{t('report.uploading', { n: progress })}</p>}
        <div className="flex justify-between gap-2 border-t border-line pt-4">
          {step > 0 ? <Button variant="secondary" icon="arrowLeft" onClick={() => setStep(step - 1)} disabled={busy}>{t('common.previous')}</Button> : <span />}
          {step < 2
            ? <Button disabled={!canNext} onClick={() => setStep(step + 1)}>{t('common.next')}</Button>
            : <Button variant="teal" size="lg" icon="send" busy={busy} onClick={submit}>{t('report.send')}</Button>}
        </div>
      </Card>
    </div>
  )
}

/* ------------------------------------------------------------------ Report detail + messages */
export function ReportDetail() {
  const { id } = useParams()
  const { t, lang } = useI18n()
  const { data: r, error, loading, reload } = useApi(`/my/reports/${id}/`)
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)
  const [showOriginal, setShowOriginal] = useState({})
  usePolling(reload, 30000)
  if (loading) return <Loading />
  if (error) return <ErrorState error={error} onRetry={reload} />

  const send = async (e) => {
    e.preventDefault()
    if (!text.trim()) return
    setBusy(true); setErr(null)
    try { await api.post(`/my/reports/${id}/reply/`, { text }); setText(''); reload() }
    catch (e2) { setErr(describeError(e2, t).message) } finally { setBusy(false) }
  }

  return (
    <div className="space-y-5">
      <Link to="/me" className="inline-flex items-center gap-1 text-sm font-semibold text-teal"><Icon name="arrowLeft" className="h-4 w-4" />{t('ben.nav.home')}</Link>
      <ReportCardHeader r={r} />
      {r.case && (
        <Link to={`/me/cases/${r.case.id}`} className="flex items-center justify-between gap-3 rounded-2xl bg-navy p-5 text-white shadow-card hover:bg-deep">
          <span><span className="block text-xs uppercase tracking-wider text-white/60">{t('report.caseNumber')}</span><span className="font-mono text-lg font-semibold">{r.case.reference}</span></span>
          <span className="inline-flex items-center gap-1 font-semibold">{t('report.followCase')}<Icon name="arrowRight" className="h-4 w-4" /></span>
        </Link>
      )}
      <Card className="p-5">
        <h2 className="font-semibold text-navy">{t('report.conversation')}</h2>
        <p className="text-sm text-muted">{t('report.conversationHint')}</p>
        <ol className="mt-4 space-y-3">
          {r.messages.length === 0 && <li className="text-sm text-muted">{t('report.noMessages')}</li>}
          {r.messages.map((m) => (
            <li key={m.id} className={`flex ${m.from_police ? 'justify-start' : 'justify-end'}`}>
              <div className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm ${m.from_police ? 'rounded-tl-sm bg-ivory text-ink' : 'rounded-tr-sm bg-teal text-white'}`}>
                <p className={`mb-1 text-xs font-semibold ${m.from_police ? 'text-teal-700' : 'text-white/80'}`}>{m.from_police ? t('report.police') : t('report.you')} · {fmtDateTime(m.created_at, lang)}</p>
                <p className="whitespace-pre-wrap">{showOriginal[m.id] ? m.original : m.text}</p>
                {m.machine_translated && (
                  <button className="mt-1 text-xs font-semibold underline" onClick={() => setShowOriginal((s) => ({ ...s, [m.id]: !s[m.id] }))}>
                    {showOriginal[m.id] ? t('report.showTranslation') : t('report.autoTranslated')}
                  </button>
                )}
              </div>
            </li>
          ))}
        </ol>
        {r.status !== 'NOT_REGISTERED' && (
          <form onSubmit={send} className="mt-4 flex gap-2">
            <label className="sr-only" htmlFor="reply">{t('report.replyLabel')}</label>
            <Textarea id="reply" rows={2} maxLength={2000} placeholder={t('report.replyPlaceholder')} value={text} onChange={(e) => setText(e.target.value)} />
            <Button type="submit" icon="send" busy={busy} disabled={!text.trim()} className="self-end">{t('report.sendReply')}</Button>
          </form>
        )}
        {err && <div className="mt-3"><Alert tone="danger">{err}</Alert></div>}
      </Card>
      <Alert tone="bronze" title={t('report.privacyTitle')}>{t('report.privacyBody')}</Alert>
    </div>
  )
}

function ReportCardHeader({ r }) {
  const { t, lang } = useI18n()
  return (
    <Card className="p-5">
      <p className="text-xs font-semibold uppercase tracking-wider text-muted">{t('report.yourReport')}</p>
      <p className="font-mono text-xl font-semibold text-navy">{r.reference}</p>
      <p className="text-xs text-muted">{t('report.sentOn', { date: fmtDateTime(r.created_at, lang) })}</p>
      <div className="mt-4"><ReportProgress status={r.status} /></div>
      <div className="mt-4"><StatusMessage r={r} /></div>
    </Card>
  )
}
