import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { api, describeError } from '../../api/client'
import { useAuth } from '../../auth/AuthContext'
import {
  Alert, Badge, Button, Card, CardHeader, Checkbox, Detail, EmptyState, ErrorState, Field, Icon, Input, Loading, Modal,
  PageHeader, PriorityBadge, Select, StatusBadge, Tabs, Textarea,
} from '../../components/ui'
import DocumentsPanel, { DOC_CATEGORIES, FilePicker, uploadDocument } from '../../components/Documents'
import { useApi } from '../../hooks/useApi'
import { useI18n } from '../../i18n'
import { fmtDate, fmtDateTime, isoToLocalInput, localInputToIso } from '../../lib/format'
import { APPOINTMENT_TYPES, JOURNEY, REFERRAL_CATEGORIES } from '../../lib/labels'

/* ---------------- Timeline ---------------- */
const CAT_ICON = { REGISTRATION: 'folder', STAGE_CHANGE: 'arrowRight', MEDICAL: 'heart', FORENSIC: 'file', PROSECUTION: 'file', COURT: 'calendar', WELFARE: 'users', APPOINTMENT: 'calendar', REFERRAL: 'send' }

export function Timeline({ items, onReviewed, canReview, currentUserId }) {
  const { t, lang } = useI18n()
  const [busy, setBusy] = useState(null)
  if (!items.length) return <EmptyState icon="clock" title={t('timeline.empty')} />
  const review = async (id, approve) => {
    setBusy(id)
    try { await api.post(`/case-updates/${id}/review/`, { approve }); onReviewed?.() } finally { setBusy(null) }
  }
  return (
    <ol className="relative ml-3 space-y-5 border-l-2 border-line pl-6">
      {[...items].reverse().map((u) => (
        <li key={u.id} className="relative">
          <span className="absolute -left-[37px] top-0.5 flex h-6 w-6 items-center justify-center rounded-full border-2 border-white bg-teal-50 text-teal ring-1 ring-line">
            <Icon name={CAT_ICON[u.category] || 'msg'} className="h-3.5 w-3.5" />
          </span>
          <div className="flex flex-wrap items-center gap-2 text-xs text-muted">
            <time dateTime={u.created_at}>{fmtDateTime(u.created_at, lang)}</time>
            <span>·</span><span className="font-semibold text-ink">{u.institution.name}</span>
            {u.author && <span>· {u.author.full_name}</span>}
            {u.visibility === 'INTERNAL' && <Badge tone="neutral" icon="shield">{t('timeline.internal')}</Badge>}
            {u.system_generated && <Badge tone="neutral" icon={null}>{t('timeline.automatic')}</Badge>}
          </div>
          <p className="mt-1 text-ink">{u.note}</p>
          {u.beneficiary_message && (
            <div className="mt-2 rounded-lg border border-line bg-ivory/70 p-3 text-sm">
              <div className="mb-1 flex flex-wrap items-center gap-2">
                <span className="text-xs font-semibold uppercase tracking-wide text-muted">{t('timeline.familyMessage')}</span>
                <StatusBadge status={u.beneficiary_status} group="reviewStatus" />
              </div>
              <p className="text-ink">“{u.beneficiary_message}”</p>
              {u.beneficiary_status === 'PENDING' && canReview && (
                u.author?.id === currentUserId
                  ? <p className="mt-2 text-xs text-muted">{t('timeline.needsOtherReviewer')}</p>
                  : <div className="mt-2 flex gap-2">
                    <Button size="sm" variant="teal" busy={busy === u.id} onClick={() => review(u.id, true)}>{t('timeline.approve')}</Button>
                    <Button size="sm" variant="secondary" disabled={busy === u.id} onClick={() => review(u.id, false)}>{t('timeline.reject')}</Button>
                  </div>
              )}
            </div>
          )}
        </li>
      ))}
    </ol>
  )
}

/* ---------------- Modals ---------------- */
function StageModal({ c, open, onClose, onDone }) {
  const { t } = useI18n()
  const [error, setError] = useState(null)
  const { register, handleSubmit, formState: { isSubmitting } } = useForm()
  const submit = async (v) => {
    setError(null)
    try { await api.post(`/cases/${c.id}/change-stage/`, v); onDone(); onClose() } catch (e) { setError(describeError(e, t).message) }
  }
  return (
    <Modal open={open} onClose={onClose} title={t('caseDetail.changeStage')}>
      <form id="stage-form" onSubmit={handleSubmit(submit)} className="space-y-4">
        <Alert tone="info">{t('caseDetail.stageHint')}</Alert>
        <Field label={t('caseDetail.newStage')} required>
          {(a) => <Select {...a} {...register('stage', { required: true })}>
            {c.can.set_stages.filter((s) => s !== c.stage.code).map((s) => <option key={s} value={s}>{t(`stage.${s}`)}</option>)}
          </Select>}
        </Field>
        <Field label={t('caseDetail.note')} hint={t('caseDetail.noteHint')}>{(a) => <Textarea {...a} maxLength={500} {...register('note')} />}</Field>
        {error && <Alert tone="danger">{error}</Alert>}
        <div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={onClose}>{t('common.cancel')}</Button><Button type="submit" busy={isSubmitting}>{t('common.save')}</Button></div>
      </form>
    </Modal>
  )
}

function UpdateModal({ c, open, onClose, onDone }) {
  const { t } = useI18n()
  const [error, setError] = useState(null)
  const { register, handleSubmit, watch, formState: { isSubmitting }, reset } = useForm({ defaultValues: { visibility: 'CASE_TEAM', category: 'GENERAL', family: false } })
  const family = watch('family')
  const submit = async ({ family: f, ...v }) => {
    setError(null)
    if (!f) { delete v.beneficiary_message; delete v.beneficiary_journey_step }
    try { await api.post(`/cases/${c.id}/updates/`, v); reset(); onDone(); onClose() } catch (e) { setError(describeError(e, t).message) }
  }
  return (
    <Modal open={open} onClose={onClose} title={t('caseDetail.addUpdate')} wide>
      <form onSubmit={handleSubmit(submit)} className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label={t('caseDetail.category')}>{(a) => <Select {...a} {...register('category')}>
            {['GENERAL', 'INVESTIGATION', 'MEDICAL', 'FORENSIC', 'PROSECUTION', 'COURT', 'WELFARE', 'SUPPORT'].map((x) => <option key={x} value={x}>{t(`updateCategory.${x}`)}</option>)}</Select>}</Field>
          <Field label={t('caseDetail.visibility')}>{(a) => <Select {...a} {...register('visibility')}>
            <option value="CASE_TEAM">{t('visibility.CASE_TEAM')}</option><option value="INTERNAL">{t('visibility.INTERNAL')}</option></Select>}</Field>
        </div>
        <Field label={t('caseDetail.internalNote')} required>{(a) => <Textarea {...a} maxLength={2000} {...register('note', { required: true })} />}</Field>
        <Checkbox label={t('caseDetail.proposeFamily')} hint={t('caseDetail.proposeFamilyHint')} {...register('family')} />
        {family && (
          <div className="space-y-4 rounded-xl border border-bronze/30 bg-bronze-50 p-4">
            <Field label={t('caseDetail.familyMessage')} hint={t('caseDetail.familyMessageHint')}>{(a) => <Textarea {...a} maxLength={400} {...register('beneficiary_message')} />}</Field>
            <Field label={t('caseDetail.journeyStep')}>{(a) => <Select {...a} {...register('beneficiary_journey_step')}>
              <option value="">—</option>{JOURNEY.map((j) => <option key={j} value={j}>{t(`journey.${j}`)}</option>)}</Select>}</Field>
          </div>
        )}
        {error && <Alert tone="danger">{error}</Alert>}
        <div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={onClose}>{t('common.cancel')}</Button><Button type="submit" busy={isSubmitting}>{t('common.save')}</Button></div>
      </form>
    </Modal>
  )
}

export function ReferralModal({ c, open, onClose, onDone }) {
  const { t } = useI18n()
  const opts = useApi(open ? '/referrals/options/' : null)
  const [error, setError] = useState(null)
  const defaults = { attach_category: 'POLICE_FILE', category: c.referral_needs?.[0] || 'MEDICAL', priority: c.immediate_risk ? 'URGENT' : 'ROUTINE', shared_fields: ['age_range', 'preferred_language', 'incident_category'], visible_to_beneficiary: true }
  const { register, handleSubmit, watch, formState: { isSubmitting, errors } } = useForm({ defaultValues: defaults })
  const category = watch('category')
  const [attachFile, setAttachFile] = useState(null)
  const receivers = opts.data?.receivers?.[category] || []
  const sensitive = ['protection_concerns', 'location_detail']
  const submit = async (v) => {
    setError(null)
    try {
      const { attach_category: attachCategory, ...body } = v
      const r = await api.post('/referrals/', { ...body, case_id: c.id })
      if (attachFile) {
        // Files sent with a referral are shared with the receiving institution only.
        await uploadDocument({ file: attachFile, category: attachCategory, title: '', referralId: r.data.id })
        setAttachFile(null)
      }
      onDone(r.data); onClose()
    } catch (e) { setError(describeError(e, t)) }
  }
  return (
    <Modal open={open} onClose={onClose} title={t('referralNew.title')} wide>
      {!open ? null : opts.error ? <ErrorState error={opts.error} /> : opts.loading || !opts.data ? <Loading /> : (
        <form onSubmit={handleSubmit(submit)} className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label={t('referralNew.category')} required>{(a) => <Select {...a} {...register('category')}>
              {REFERRAL_CATEGORIES.map((x) => <option key={x} value={x}>{t(`referralCategory.${x}`)}</option>)}</Select>}</Field>
            <Field label={t('referralNew.priority')}>{(a) => <Select {...a} {...register('priority')}>
              {['ROUTINE', 'URGENT', 'EMERGENCY'].map((x) => <option key={x} value={x}>{t(`priority.${x}`)}</option>)}</Select>}</Field>
          </div>
          <Field label={t('referralNew.receiver')} required error={(errors.receiving_institution_id && t('validation.required')) || error?.fields?.receiving_institution_id}>
            {(a) => <Select {...a} {...register('receiving_institution_id', { required: true })}>
              <option value="">{receivers.length ? t('common.choose') : t('referralNew.noReceivers')}</option>
              {receivers.map((r) => <option key={r.id} value={r.id}>{r.name} — {r.district}</option>)}</Select>}
          </Field>
          <Field label={t('referralNew.purpose')} hint={t('referralNew.purposeHint')} required error={errors.purpose && t('validation.required')}>
            {(a) => <Textarea {...a} maxLength={500} {...register('purpose', { required: true })} />}
          </Field>
          <fieldset className="rounded-xl border border-line p-4">
            <legend className="px-1 text-sm font-semibold text-ink">{t('referralNew.shareTitle')}</legend>
            <p className="mb-3 text-xs text-muted">{t('referralNew.shareHint')}</p>
            <div className="grid gap-2 sm:grid-cols-2">
              {Object.keys(opts.data.shareable_fields).filter((f) => c.sensitive || !sensitive.includes(f)).map((f) => (
                <Checkbox key={f} value={f} label={t(`shareable.${f}`)} hint={sensitive.includes(f) ? t('referralNew.sensitiveField') : undefined} {...register('shared_fields')} />
              ))}
            </div>
          </fieldset>
          <fieldset className="rounded-xl border border-line p-4">
            <legend className="px-1 text-sm font-semibold text-ink">{t('docs.sendWithReferral')}</legend>
            <p className="mb-3 text-xs text-muted">{t('docs.sendWithReferralHint')}</p>
            <div className="grid gap-3 sm:grid-cols-[14rem_1fr]">
              <Select aria-label={t('docs.type')} {...register('attach_category')}>{DOC_CATEGORIES.map((x) => <option key={x} value={x}>{t(`docCategory.${x}`)}</option>)}</Select>
              <FilePicker id="referral-attach" file={attachFile} onChange={setAttachFile} />
            </div>
          </fieldset>
          <Checkbox label={t('referralNew.visibleToFamily')} hint={t('referralNew.visibleToFamilyHint')} {...register('visible_to_beneficiary')} />
          {error && <Alert tone="danger">{error.message}</Alert>}
          <div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={onClose}>{t('common.cancel')}</Button><Button type="submit" icon="send" busy={isSubmitting}>{t('referralNew.send')}</Button></div>
        </form>
      )}
    </Modal>
  )
}

function AppointmentModal({ c, open, onClose, onDone, existing }) {
  const { t } = useI18n()
  const { user } = useAuth()
  const [error, setError] = useState(null)
  const types = user.role === 'COURT' ? APPOINTMENT_TYPES : APPOINTMENT_TYPES.filter((x) => x !== 'COURT_HEARING')
  const { register, handleSubmit, formState: { isSubmitting } } = useForm({
    values: existing ? { ...existing, scheduled_for: isoToLocalInput(existing.scheduled_for) }
      : { type: types[0], visible_to_beneficiary: true, attendees: 'CHILD_AND_CAREGIVER', scheduled_for: '', public_location: '', beneficiary_note: '', internal_note: '' },
  })
  const submit = async (v) => {
    setError(null)
    const body = { type: v.type, scheduled_for: localInputToIso(v.scheduled_for), public_location: v.public_location,
      beneficiary_note: v.beneficiary_note, internal_note: v.internal_note || '', visible_to_beneficiary: v.visible_to_beneficiary, attendees: v.attendees }
    if (existing) body.status = v.status
    try {
      if (existing) await api.patch(`/appointments/${existing.id}/`, body)
      else await api.post('/appointments/', { ...body, case_id: c.id })
      onDone(); onClose()
    } catch (e) { setError(describeError(e, t)) }
  }
  return (
    <Modal open={open} onClose={onClose} title={existing ? t('appointments.edit') : t('appointments.new')} wide>
      <form onSubmit={handleSubmit(submit)} className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label={t('appointments.type')}>{(a) => <Select {...a} disabled={!!existing} {...register('type')}>{types.map((x) => <option key={x} value={x}>{t(`appointmentType.${x}`)}</option>)}</Select>}</Field>
          <Field label={t('appointments.when')} required error={error?.fields?.scheduled_for}>{(a) => <Input {...a} type="datetime-local" {...register('scheduled_for', { required: true })} />}</Field>
          {existing && <Field label={t('appointments.status')}>{(a) => <Select {...a} {...register('status')}>
            {['SCHEDULED', 'RESCHEDULED', 'COMPLETED', 'MISSED', 'CANCELLED'].map((x) => <option key={x} value={x}>{t(`appointmentStatus.${x}`)}</option>)}</Select>}</Field>}
        </div>
        <Field label={t('appointments.attendees')} hint={t('appointments.attendeesHint')}>{(a) => <Select {...a} {...register('attendees')}>
          {['CHILD_AND_CAREGIVER', 'CHILD', 'CAREGIVER', 'NOT_REQUIRED'].map((x) => <option key={x} value={x}>{t(`attendees.${x}`)}</option>)}</Select>}</Field>
        <Field label={t('appointments.location')} hint={t('appointments.locationHint')} required>{(a) => <Input {...a} {...register('public_location', { required: true })} />}</Field>
        <Field label={t('appointments.familyNote')} hint={t('appointments.familyNoteHint')}>{(a) => <Input {...a} maxLength={300} {...register('beneficiary_note')} />}</Field>
        <Field label={t('appointments.internalNote')}>{(a) => <Input {...a} maxLength={500} {...register('internal_note')} />}</Field>
        <Checkbox label={t('appointments.visibleToFamily')} hint={t('appointments.visibleToFamilyHint')} {...register('visible_to_beneficiary')} />
        {error && <Alert tone="danger">{error.message}</Alert>}
        <div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={onClose}>{t('common.cancel')}</Button><Button type="submit" busy={isSubmitting}>{t('common.save')}</Button></div>
      </form>
    </Modal>
  )
}

function FollowUpModal({ c, open, onClose, onDone }) {
  const { t } = useI18n()
  const officers = useApi(open ? '/cases/officers/' : null)
  const [error, setError] = useState(null)
  const { register, handleSubmit, formState: { isSubmitting } } = useForm()
  const submit = async (v) => {
    setError(null)
    if (!v.assigned_to_id) delete v.assigned_to_id
    try { await api.post('/follow-ups/', { ...v, case_id: c.id }); onDone(); onClose() } catch (e) { setError(describeError(e, t).message) }
  }
  return (
    <Modal open={open} onClose={onClose} title={t('followUps.new')}>
      <form onSubmit={handleSubmit(submit)} className="space-y-4">
        <Field label={t('followUps.description')} required>{(a) => <Input {...a} maxLength={300} {...register('description', { required: true })} />}</Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label={t('followUps.due')} required>{(a) => <Input {...a} type="date" {...register('due_date', { required: true })} />}</Field>
          <Field label={t('followUps.assignee')}>{(a) => <Select {...a} {...register('assigned_to_id')}><option value="">{t('caseNew.me')}</option>
            {officers.data?.map((o) => <option key={o.id} value={o.id}>{o.full_name}</option>)}</Select>}</Field>
        </div>
        {error && <Alert tone="danger">{error}</Alert>}
        <div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={onClose}>{t('common.cancel')}</Button><Button type="submit" busy={isSubmitting}>{t('common.save')}</Button></div>
      </form>
    </Modal>
  )
}

function GrantModal({ c, open, onClose, onDone }) {
  const { t } = useI18n()
  const [error, setError] = useState(null)
  const { register, handleSubmit, formState: { isSubmitting } } = useForm({ defaultValues: { relationship: 'CAREGIVER' } })
  const submit = async (v) => {
    setError(null)
    try { await api.post('/access-grants/', { ...v, case_id: c.id }); onDone(); onClose() } catch (e) { const d = describeError(e, t); setError(Object.values(d.fields)[0] || d.message) }
  }
  return (
    <Modal open={open} onClose={onClose} title={t('grants.new')} wide>
      <form onSubmit={handleSubmit(submit)} className="space-y-4">
        <Alert tone="warn" title={t('grants.safeguardTitle')}>{t('grants.safeguardBody')}</Alert>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label={t('grants.username')} hint={t('grants.usernameHint')} required>{(a) => <Input {...a} autoCapitalize="none" {...register('username', { required: true })} />}</Field>
          <Field label={t('grants.relationship')}>{(a) => <Select {...a} {...register('relationship')}>
            {['CAREGIVER', 'PARENT', 'GUARDIAN', 'SOCIAL_WORKER_PROXY', 'SELF'].map((x) => <option key={x} value={x}>{t(`relationship.${x}`)}</option>)}</Select>}</Field>
        </div>
        <Field label={t('grants.basis')} hint={t('grants.basisHint')} required>{(a) => <Textarea {...a} maxLength={500} {...register('basis', { required: true })} />}</Field>
        <Field label={t('grants.validUntil')}>{(a) => <Input {...a} type="date" {...register('valid_until', { setValueAs: (v) => v || null })} />}</Field>
        <Checkbox label={t('grants.conflictCheck')} {...register('conflict_check_confirmed')} />
        {error && <Alert tone="danger">{error}</Alert>}
        <div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={onClose}>{t('common.cancel')}</Button><Button type="submit" busy={isSubmitting}>{t('grants.request')}</Button></div>
      </form>
    </Modal>
  )
}

/* ---------------- Tab panels ---------------- */
function ReferralsPanel({ c, reloadKey }) {
  const { t, lang } = useI18n()
  const { data, loading, error } = useApi(`/cases/${c.id}/referrals/`, { deps: [reloadKey] })
  if (loading) return <Loading />
  if (error) return <ErrorState error={error} />
  if (!data.length) return <EmptyState icon="send" title={t('referrals.emptyCase')}>{t('referrals.emptyCaseHint')}</EmptyState>
  return (
    <ul className="divide-y divide-line">
      {data.map((r) => (
        <li key={r.id}><Link to={`/app/referrals/${r.id}`} className="flex flex-wrap items-center gap-3 px-5 py-3.5 hover:bg-ivory">
          <div className="min-w-0 flex-1">
            <p className="font-semibold text-navy">{t(`referralCategory.${r.category}`)} <span className="font-mono text-sm text-muted">{r.reference}</span></p>
            <p className="text-sm text-muted">{r.direction === 'outgoing' ? `→ ${r.receiving_institution.name}` : `← ${r.sending_institution.name}`} · {fmtDate(r.sent_at || r.created_at, lang)}</p>
          </div>
          <PriorityBadge priority={r.priority} /><StatusBadge status={r.status} group="referralStatus" />
        </Link></li>
      ))}
    </ul>
  )
}

function AppointmentsPanel({ c, reloadKey, onEdit }) {
  const { t, lang } = useI18n()
  const { user } = useAuth()
  const { data, loading, error } = useApi(`/cases/${c.id}/appointments/`, { deps: [reloadKey] })
  if (loading) return <Loading />
  if (error) return <ErrorState error={error} />
  if (!data.length) return <EmptyState icon="calendar" title={t('appointments.empty')} />
  return (
    <ul className="divide-y divide-line">
      {data.map((a) => (
        <li key={a.id} className="flex flex-wrap items-center gap-3 px-5 py-3.5">
          <div className="min-w-0 flex-1">
            <p className="font-semibold text-navy">{t(`appointmentType.${a.type}`)} · {fmtDateTime(a.scheduled_for, lang)}</p>
            <p className="text-sm text-muted">{a.public_location} · {a.institution.name}</p>
            {a.previous_scheduled_for && <p className="text-xs text-warn-700">{t('appointments.previously', { date: fmtDateTime(a.previous_scheduled_for, lang) })}</p>}
            {a.internal_note && <p className="text-xs text-muted">{t('appointments.internalNote')}: {a.internal_note}</p>}
          </div>
          {a.visible_to_beneficiary && <Badge tone="bronze" icon="eye">{t('appointments.familySees')}</Badge>}
          <StatusBadge status={a.status} group="appointmentStatus" />
          {a.institution.id === user.institution.id && <Button size="sm" variant="secondary" onClick={() => onEdit(a)}>{t('common.edit')}</Button>}
        </li>
      ))}
    </ul>
  )
}

function FollowUpsPanel({ c, reloadKey }) {
  const { t, lang } = useI18n()
  const { data, loading, error, reload } = useApi('/follow-ups/', { params: { case: c.id }, deps: [reloadKey] })
  if (loading) return <Loading />
  if (error) return <ErrorState error={error} />
  if (!data.results.length) return <EmptyState icon="list" title={t('followUps.emptyCase')} />
  return <FollowUpList items={data.results} onChanged={reload} lang={lang} />
}

export function FollowUpList({ items, onChanged, lang, showCase }) {
  const { t } = useI18n()
  const [busy, setBusy] = useState(null)
  const done = async (f) => {
    const outcome = window.prompt(t('followUps.outcomePrompt'))
    if (outcome === null) return
    setBusy(f.id)
    try { await api.patch(`/follow-ups/${f.id}/`, { status: 'DONE', outcome_note: outcome }); onChanged() } finally { setBusy(null) }
  }
  const overdue = (f) => f.status === 'PENDING' && new Date(f.due_date) < new Date(new Date().toDateString())
  return (
    <ul className="divide-y divide-line">
      {items.map((f) => (
        <li key={f.id} className="flex flex-wrap items-center gap-3 px-5 py-3.5">
          <div className="min-w-0 flex-1">
            <p className="font-semibold text-navy">{f.description}</p>
            <p className="text-sm text-muted">
              {showCase && <Link to={`/app/cases/${f.case_id}`} className="font-mono text-teal hover:underline">{f.case_reference}</Link>}{showCase && ' · '}
              {t('followUps.dueOn', { date: fmtDate(f.due_date, lang) })} · {f.assigned_to.full_name}
            </p>
            {f.outcome_note && <p className="text-xs text-muted">{t('followUps.outcome')}: {f.outcome_note}</p>}
          </div>
          {overdue(f) && <Badge tone="danger">{t('followUps.overdue')}</Badge>}
          <StatusBadge status={f.status} group="followUpStatus" />
          {f.status === 'PENDING' && <Button size="sm" variant="secondary" icon="check" busy={busy === f.id} onClick={() => done(f)}>{t('followUps.markDone')}</Button>}
        </li>
      ))}
    </ul>
  )
}

function FamilyPanel({ c, reloadKey, onNewGrant }) {
  const { t, lang } = useI18n()
  const grants = useApi(c.can.manage_access ? `/cases/${c.id}/grants/` : null, { deps: [reloadKey] })
  const reqs = useApi(c.can.review_beneficiary_updates ? `/cases/${c.id}/assistance-requests/` : null, { deps: [reloadKey] })
  const [busy, setBusy] = useState(null)
  const act = async (g, verb) => {
    let body = {}
    if (verb === 'revoke') {
      const reason = window.prompt(t('grants.revokePrompt'))
      if (!reason) return
      body = { reason }
    }
    setBusy(g.id)
    try { await api.post(`/access-grants/${g.id}/${verb}/`, body); grants.reload() } catch (e) { window.alert(describeError(e, t).message) } finally { setBusy(null) }
  }
  if (!c.can.manage_access && !c.can.review_beneficiary_updates) return <div className="p-5"><Alert>{t('grants.notPermitted')}</Alert></div>
  return (
    <div className="space-y-6 p-5">
      {c.can.manage_access && (
        <section>
          <div className="mb-3 flex items-center justify-between">
            <h3 className="font-semibold text-navy">{t('grants.title')}</h3>
            <Button size="sm" icon="plus" onClick={onNewGrant}>{t('grants.new')}</Button>
          </div>
          {grants.loading ? <Loading /> : !grants.data?.length ? <p className="text-sm text-muted">{t('grants.empty')}</p> : (
            <ul className="divide-y divide-line rounded-xl border border-line">
              {grants.data.map((g) => (
                <li key={g.id} className="flex flex-wrap items-center gap-3 p-4">
                  <div className="min-w-0 flex-1">
                    <p className="font-semibold text-ink">{g.user.full_name || g.user.username} <span className="font-mono text-xs text-muted">({g.user.username})</span></p>
                    <p className="text-sm text-muted">{t(`relationship.${g.relationship}`)} · {t('grants.requestedBy', { name: g.created_by.full_name })}{g.approved_by && ` · ${t('grants.approvedBy', { name: g.approved_by.full_name })}`}</p>
                    <p className="text-xs text-muted">{g.basis}</p>
                  </div>
                  <StatusBadge status={g.status} group="grantStatus" />
                  {g.status === 'PENDING' && <Button size="sm" variant="teal" busy={busy === g.id} onClick={() => act(g, 'approve')}>{t('grants.approve')}</Button>}
                  {g.status !== 'REVOKED' && <Button size="sm" variant="secondary" disabled={busy === g.id} onClick={() => act(g, 'revoke')}>{t('grants.revoke')}</Button>}
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
      {c.can.review_beneficiary_updates && (
        <section>
          <h3 className="mb-3 font-semibold text-navy">{t('assistance.titleCase')}</h3>
          {reqs.loading ? <Loading /> : !reqs.data?.length ? <p className="text-sm text-muted">{t('assistance.empty')}</p> : (
            <ul className="divide-y divide-line rounded-xl border border-line">
              {reqs.data.map((r) => (
                <li key={r.id} className="flex flex-wrap items-center gap-3 p-4">
                  <div className="min-w-0 flex-1"><p className="font-semibold">{t(`assistanceType.${r.request_type}`)}</p><p className="text-sm text-muted">{r.message || '—'} · {fmtDateTime(r.created_at, lang)}</p></div>
                  <StatusBadge status={r.status} group="assistanceStatus" />
                  <Link to="/app/assistance" className="text-sm font-semibold text-teal">{t('assistance.respond')}</Link>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
    </div>
  )
}

/* ---------------- Page ---------------- */
export default function CaseDetail() {
  const { id } = useParams()
  const [params, setParams] = useSearchParams()
  const { t, lang } = useI18n()
  const { user } = useAuth()
  const { data: c, error, loading, reload } = useApi(`/cases/${id}/`)
  const timeline = useApi(`/cases/${id}/timeline/`)
  const [reloadKey, setReloadKey] = useState(0)
  const [modal, setModal] = useState(null)
  const [editAppt, setEditAppt] = useState(null)
  const tab = params.get('tab') || 'overview'
  const refreshAll = () => { reload(); timeline.reload(); setReloadKey((k) => k + 1) }

  if (loading) return <Loading />
  if (error) return <ErrorState error={error} onRetry={reload} />

  const pendingFamily = (timeline.data || []).filter((u) => u.beneficiary_status === 'PENDING').length
  const tabs = [
    { id: 'overview', label: t('caseDetail.tabs.overview') },
    { id: 'timeline', label: t('caseDetail.tabs.timeline'), count: pendingFamily || undefined },
    { id: 'referrals', label: t('caseDetail.tabs.referrals') },
    { id: 'appointments', label: t('caseDetail.tabs.appointments') },
    { id: 'followups', label: t('caseDetail.tabs.followUps') },
    { id: 'documents', label: t('caseDetail.tabs.documents') },
    { id: 'family', label: t('caseDetail.tabs.family') },
  ]
  const close = () => { setModal(null); setEditAppt(null) }

  return (
    <>
      <PageHeader
        back={<Link to="/app/cases" className="mb-2 inline-flex items-center gap-1 text-sm font-semibold text-teal"><Icon name="arrowLeft" className="h-4 w-4" />{t('nav.cases')}</Link>}
        title={<span className="font-mono">{c.reference}</span>}
        subtitle={`${c.child_pseudonym} · ${t(`age.${c.age_range}`)} · ${t(`incident.${c.incident_category}`)}`}
        actions={<>
          {c.can.set_stages.length > 0 && <Button variant="secondary" icon="arrowRight" onClick={() => setModal('stage')}>{t('caseDetail.changeStage')}</Button>}
          <Button variant="secondary" icon="msg" onClick={() => setModal('update')}>{t('caseDetail.addUpdate')}</Button>
          {c.can.create_referral && <Button icon="send" onClick={() => setModal('referral')}>{t('caseDetail.refer')}</Button>}
        </>}
      />
      {params.get('created') && <div className="mb-5"><Alert tone="success" title={t('caseDetail.createdTitle')}>{t('caseDetail.createdBody', { ref: c.reference })}</Alert></div>}

      <div className="mb-5 flex flex-wrap items-center gap-2">
        <Badge tone="info" icon="arrowRight">{t(`stage.${c.stage.code}`)}</Badge>
        {c.immediate_risk && <Badge tone="danger">{t('cases.immediateRisk')}</Badge>}
        {c.closed_at && <Badge tone="success">{t('caseDetail.closed')}</Badge>}
        {!c.is_lead && <Badge tone="neutral" icon="shield">{t('caseDetail.teamMemberAccess')}</Badge>}
      </div>

      <Tabs tabs={tabs} value={tab} onChange={(v) => setParams(v === 'overview' ? {} : { tab: v })} />

      {tab === 'overview' && (
        <div className="grid gap-6 lg:grid-cols-[1fr_22rem]">
          <Card>
            <CardHeader title={t('caseDetail.summary')} />
            <dl className="grid gap-5 p-5 sm:grid-cols-2">
              <Detail label={t('cases.reported')}>{fmtDate(c.date_reported, lang)}</Detail>
              <Detail label={t('cases.lead')}>{c.lead_institution.name}</Detail>
              <Detail label={t('caseNew.assignedOfficer')}>{c.assigned_officer.full_name}</Detail>
              <Detail label={t('caseNew.district')}>{c.district} · {t(`region.${c.region}`)}</Detail>
              <Detail label={t('caseNew.language')}>{t(`languages.${c.preferred_language}`)}</Detail>
              <Detail label={t('caseNew.externalRef')}>{c.external_reference || '—'}</Detail>
              <Detail label={t('caseNew.needsSection')}>{c.referral_needs.length ? c.referral_needs.map((n) => t(`referralCategory.${n}`)).join(', ') : '—'}</Detail>
              <Detail label={t('caseDetail.lastUpdated')}>{fmtDateTime(c.updated_at, lang)}</Detail>
            </dl>
            {c.sensitive ? (
              <div className="m-5 mt-0 rounded-xl border border-bronze/30 bg-bronze-50 p-4">
                <p className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-[#6b5636]"><Icon name="shield" className="h-4 w-4" />{t('caseDetail.restricted')}</p>
                <dl className="grid gap-4 sm:grid-cols-2">
                  <Detail label={t('caseNew.protectionConcerns')}>{c.sensitive.protection_concerns || '—'}</Detail>
                  <Detail label={t('caseNew.locationDetail')}>{c.sensitive.location_detail || '—'}</Detail>
                </dl>
              </div>
            ) : (
              <div className="m-5 mt-0"><Alert tone="info">{t('caseDetail.restrictedHidden')}</Alert></div>
            )}
          </Card>
          <div className="space-y-6">
            <Card>
              <CardHeader title={t('caseDetail.team')} />
              <ul className="divide-y divide-line">
                {c.team.map((m) => (
                  <li key={m.institution.id} className="px-5 py-3">
                    <p className="font-semibold text-ink">{m.institution.name}</p>
                    <p className="text-sm text-muted">{m.is_lead ? t('caseDetail.leadInstitution') : t(`referralCategory.${m.role_in_case}`)}{m.officer && ` · ${m.officer}`}</p>
                  </li>
                ))}
              </ul>
            </Card>
            <Card className="p-5">
              <h3 className="font-semibold text-navy">{t('caseDetail.quickActions')}</h3>
              <div className="mt-3 grid gap-2">
                <Button variant="secondary" icon="calendar" onClick={() => setModal('appointment')}>{user.role === 'COURT' ? t('appointments.scheduleHearing') : t('appointments.new')}</Button>
                <Button variant="secondary" icon="list" onClick={() => setModal('followup')}>{t('followUps.new')}</Button>
              </div>
            </Card>
          </div>
        </div>
      )}

      {tab === 'timeline' && (
        <Card className="p-5">
          <Alert tone="bronze">{t('timeline.reviewRule')}</Alert>
          <div className="mt-6">{timeline.loading ? <Loading /> : timeline.error ? <ErrorState error={timeline.error} /> :
            <Timeline items={timeline.data} canReview={c.can.review_beneficiary_updates} currentUserId={user.id} onReviewed={refreshAll} />}</div>
        </Card>
      )}
      {tab === 'referrals' && <Card>
        <CardHeader title={t('caseDetail.tabs.referrals')} action={c.can.create_referral && <Button size="sm" icon="plus" onClick={() => setModal('referral')}>{t('caseDetail.refer')}</Button>} />
        <ReferralsPanel c={c} reloadKey={reloadKey} /></Card>}
      {tab === 'appointments' && <Card>
        <CardHeader title={t('caseDetail.tabs.appointments')} action={<Button size="sm" icon="plus" onClick={() => setModal('appointment')}>{user.role === 'COURT' ? t('appointments.scheduleHearing') : t('appointments.new')}</Button>} />
        <AppointmentsPanel c={c} reloadKey={reloadKey} onEdit={(a) => { setEditAppt(a); setModal('appointment') }} /></Card>}
      {tab === 'followups' && <Card>
        <CardHeader title={t('caseDetail.tabs.followUps')} action={<Button size="sm" icon="plus" onClick={() => setModal('followup')}>{t('followUps.new')}</Button>} />
        <FollowUpsPanel c={c} reloadKey={reloadKey} /></Card>}
      {tab === 'documents' && <Card><CardHeader title={t('caseDetail.tabs.documents')} subtitle={t('docs.caseSubtitle')} /><div className="p-5"><DocumentsPanel caseId={c.id} /></div></Card>}
      {tab === 'family' && <Card><CardHeader title={t('caseDetail.tabs.family')} subtitle={t('grants.subtitle')} /><FamilyPanel c={c} reloadKey={reloadKey} onNewGrant={() => setModal('grant')} /></Card>}

      <StageModal c={c} open={modal === 'stage'} onClose={close} onDone={refreshAll} />
      <UpdateModal c={c} open={modal === 'update'} onClose={close} onDone={refreshAll} />
      <ReferralModal c={c} open={modal === 'referral'} onClose={close} onDone={() => { refreshAll(); setParams({ tab: 'referrals' }) }} />
      <AppointmentModal c={c} open={modal === 'appointment'} existing={editAppt} onClose={close} onDone={refreshAll} />
      <FollowUpModal c={c} open={modal === 'followup'} onClose={close} onDone={refreshAll} />
      <GrantModal c={c} open={modal === 'grant'} onClose={close} onDone={refreshAll} />
    </>
  )
}
