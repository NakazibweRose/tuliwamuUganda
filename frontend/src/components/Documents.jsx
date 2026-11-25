import { useState } from 'react'
import { api, describeError } from '../api/client'
import { useApi } from '../hooks/useApi'
import { useI18n } from '../i18n'
import { fmtDateTime } from '../lib/format'
import { Alert, Badge, Button, Checkbox, EmptyState, ErrorState, Field, Icon, Input, Loading, Modal, Select } from './ui'

export const DOC_CATEGORIES = ['MEDICAL_REPORT', 'MEDICAL_FORM', 'FORENSIC_REPORT', 'POLICE_FILE', 'STATEMENT', 'PROSECUTION_DOCUMENT', 'COURT_DOCUMENT', 'WELFARE_REPORT', 'LEGAL_DOCUMENT', 'OTHER']
export const ACCEPT = '.pdf,.jpg,.jpeg,.png,.webp,.docx,application/pdf,image/jpeg,image/png,image/webp,application/vnd.openxmlformats-officedocument.wordprocessingml.document'
const MAX = 10 * 1024 * 1024

/** Sensible default document type for an upload on a referral, by referral type and side. */
export function defaultCategory(referral) {
  if (!referral) return 'STATEMENT'
  const incoming = referral.direction === 'incoming'
  const map = incoming
    ? { MEDICAL: 'MEDICAL_REPORT', FORENSIC: 'FORENSIC_REPORT', PROSECUTION: 'PROSECUTION_DOCUMENT', COURT: 'COURT_DOCUMENT', PROBATION: 'WELFARE_REPORT', LEGAL_AID: 'LEGAL_DOCUMENT' }
    : { PROSECUTION: 'POLICE_FILE', COURT: 'PROSECUTION_DOCUMENT', FORENSIC: 'STATEMENT' }
  return map[referral.category] || 'OTHER'
}

const kb = (n) => (n > 1024 * 1024 ? `${(n / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1024))} KB`)

/** Upload one file. Returns the created document. */
export async function uploadDocument({ file, category, title, caseId, referralId, forwardable = true }) {
  const fd = new FormData()
  fd.append('file', file)
  fd.append('category', category)
  fd.append('title', title || '')
  fd.append('forwardable', String(forwardable))
  if (referralId) fd.append('referral_id', referralId)
  else fd.append('case_id', caseId)
  return (await api.post('/documents/', fd, { timeout: 120000 })).data
}

/** File picker with type/size checks before upload. */
export function FilePicker({ file, onChange, id }) {
  const { t } = useI18n()
  const [err, setErr] = useState(null)
  return (
    <div>
      <label htmlFor={id} className="flex min-h-[56px] cursor-pointer items-center gap-3 rounded-lg border border-dashed border-line bg-ivory/60 px-3 hover:border-teal">
        <Icon name="file" className="h-5 w-5 shrink-0 text-teal" />
        <span className="min-w-0 flex-1 truncate text-sm">{file ? `${file.name} · ${kb(file.size)}` : t('docs.chooseFile')}</span>
        <input id={id} type="file" accept={ACCEPT} className="sr-only" onChange={(e) => {
          const f = e.target.files?.[0]
          setErr(null)
          if (f && f.size > MAX) { setErr(t('docs.tooLarge')); onChange(null); return }
          onChange(f || null)
        }} />
      </label>
      <p className={`mt-1 text-xs ${err ? 'text-danger-700' : 'text-muted'}`}>{err || t('docs.allowed')}</p>
    </div>
  )
}

async function download(doc) {
  const r = await api.get(`/documents/${doc.id}/download/`, { responseType: 'blob', timeout: 120000 })
  const url = URL.createObjectURL(r.data)
  const a = document.createElement('a')
  a.href = url
  a.download = doc.filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 5000)
}

function ForwardModal({ doc, onClose, onDone }) {
  const { t } = useI18n()
  const targets = useApi(doc ? `/documents/${doc.id}/share-targets/` : null)
  const [target, setTarget] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)
  const submit = async () => {
    setBusy(true); setErr(null)
    try { await api.post(`/documents/${doc.id}/share/`, { institution_id: target }); onDone(); onClose() }
    catch (e) { setErr(describeError(e, t).message) } finally { setBusy(false) }
  }
  return (
    <Modal open={!!doc} onClose={onClose} title={t('docs.forwardTitle')}>
      {!doc ? null : targets.loading || !targets.data ? <Loading /> : (
        <>
          <p className="text-sm text-ink"><span className="font-semibold">{doc.title}</span> · {t(`docCategory.${doc.category}`)}</p>
          <Alert tone="warn">{t('docs.forwardWarning')}</Alert>
          {targets.data.length === 0 ? <p className="text-sm text-muted">{t('docs.noTargets')}</p> : (
            <Field label={t('docs.forwardTo')}>{(a) => <Select {...a} value={target} onChange={(e) => setTarget(e.target.value)}>
              <option value="">{t('common.choose')}</option>{targets.data.map((i) => <option key={i.id} value={i.id}>{i.name}</option>)}</Select>}</Field>
          )}
          {err && <Alert tone="danger">{err}</Alert>}
          <div className="flex justify-end gap-2"><Button variant="secondary" onClick={onClose}>{t('common.cancel')}</Button><Button icon="send" busy={busy} disabled={!target} onClick={submit}>{t('docs.forward')}</Button></div>
        </>
      )}
    </Modal>
  )
}

/**
 * Documents for a case (optionally only those on one referral), with upload.
 * The list only ever contains documents the API says this institution may see.
 */
export default function DocumentsPanel({ caseId, referral, canUpload = true, hint }) {
  const { t, lang } = useI18n()
  const params = referral ? { referral: referral.id } : { case: caseId }
  const { data, error, loading, reload } = useApi('/documents/', { params })
  const [file, setFile] = useState(null)
  const [category, setCategory] = useState(defaultCategory(referral))
  const [title, setTitle] = useState('')
  const [forwardable, setForwardable] = useState(true)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)
  const [forward, setForward] = useState(null)
  const [open, setOpen] = useState(false)

  const submit = async () => {
    setBusy(true); setErr(null)
    try {
      await uploadDocument({ file, category, title, caseId, referralId: referral?.id, forwardable })
      setFile(null); setTitle(''); setOpen(false); reload()
    } catch (e) { const d = describeError(e, t); setErr(d.fields.file || d.fields.category || d.message) } finally { setBusy(false) }
  }
  const withdraw = async (doc) => {
    const reason = window.prompt(t('docs.withdrawPrompt'))
    if (!reason) return
    try { await api.post(`/documents/${doc.id}/withdraw/`, { reason }); reload() } catch (e) { window.alert(describeError(e, t).message) }
  }

  return (
    <div className="space-y-4">
      {hint && <Alert tone="bronze">{hint}</Alert>}
      {loading ? <Loading /> : error ? <ErrorState error={error} onRetry={reload} /> : data.length === 0 ? (
        <EmptyState icon="file" title={t('docs.empty')}>{t('docs.emptyHint')}</EmptyState>
      ) : (
        <ul className="divide-y divide-line rounded-xl border border-line">
          {data.map((d) => (
            <li key={d.id} className="flex flex-wrap items-center gap-3 p-4">
              <span className="rounded-lg bg-teal-50 p-2 text-teal"><Icon name="file" className="h-5 w-5" /></span>
              <div className="min-w-0 flex-1">
                <p className="truncate font-semibold text-navy">{d.title}</p>
                <p className="text-xs text-muted">{t(`docCategory.${d.category}`)} · {d.filename} · {kb(d.size_bytes)}</p>
                <p className="text-xs text-muted">{t('docs.from', { institution: d.institution.name, name: d.uploaded_by })} · {fmtDateTime(d.created_at, lang)}{d.referral && !referral ? ` · ${t('docs.onReferral', { ref: d.referral.reference })}` : ''}</p>
                {d.shared_with && <p className="mt-0.5 text-xs text-muted"><Icon name="eye" className="mr-1 inline h-3.5 w-3.5" />{d.shared_with.length ? t('docs.sharedWith', { list: d.shared_with.join(', ') }) : t('docs.notShared')}</p>}
              </div>
              {!d.forwardable && <Badge tone="warn" icon="shield">{t('docs.noForward')}</Badge>}
              <Button size="sm" variant="secondary" icon="arrowRight" onClick={() => download(d).catch((e) => window.alert(describeError(e, t).message))}>{t('docs.download')}</Button>
              {d.can_forward && <Button size="sm" variant="ghost" icon="send" onClick={() => setForward(d)}>{t('docs.forward')}</Button>}
              {d.is_own && <Button size="sm" variant="ghost" onClick={() => withdraw(d)}>{t('docs.withdraw')}</Button>}
            </li>
          ))}
        </ul>
      )}

      {canUpload && (open ? (
        <div className="space-y-3 rounded-xl border border-line p-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label={t('docs.type')}>{(a) => <Select {...a} value={category} onChange={(e) => setCategory(e.target.value)}>
              {DOC_CATEGORIES.map((c) => <option key={c} value={c}>{t(`docCategory.${c}`)}</option>)}</Select>}</Field>
            <Field label={t('docs.title')}>{(a) => <Input {...a} maxLength={150} value={title} onChange={(e) => setTitle(e.target.value)} placeholder={t('docs.titlePlaceholder')} />}</Field>
          </div>
          <FilePicker id={`doc-file-${referral?.id || caseId}`} file={file} onChange={setFile} />
          <Checkbox label={t('docs.forwardable')} hint={t('docs.forwardableHint')} checked={forwardable} onChange={(e) => setForwardable(e.target.checked)} />
          <p className="text-xs text-muted"><Icon name="shield" className="mr-1 inline h-3.5 w-3.5" />{referral ? t('docs.whoSeesReferral', { other: referral.direction === 'incoming' ? referral.sending_institution.name : referral.receiving_institution.name }) : t('docs.whoSeesCase')}</p>
          {err && <Alert tone="danger">{err}</Alert>}
          <div className="flex justify-end gap-2"><Button variant="secondary" onClick={() => setOpen(false)}>{t('common.cancel')}</Button><Button icon="plus" busy={busy} disabled={!file} onClick={submit}>{t('docs.upload')}</Button></div>
        </div>
      ) : <Button variant="secondary" icon="plus" onClick={() => setOpen(true)}>{t('docs.addDocument')}</Button>)}

      <ForwardModal doc={forward} onClose={() => setForward(null)} onDone={reload} />
    </div>
  )
}
