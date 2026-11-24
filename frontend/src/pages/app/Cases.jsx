import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate } from 'react-router-dom'
import { api, describeError } from '../../api/client'
import { useAuth } from '../../auth/AuthContext'
import { Alert, Badge, Button, Card, Checkbox, EmptyState, ErrorState, Field, Icon, Input, Loading, PageHeader, Select, Table, Textarea } from '../../components/ui'
import { useApi } from '../../hooks/useApi'
import { useI18n } from '../../i18n'
import { fmtDate } from '../../lib/format'
import { AGE_RANGES, INCIDENT_CATEGORIES, LANG_CODES, REFERRAL_NEEDS, REGIONS } from '../../lib/labels'

export function CaseList() {
  const { t, lang } = useI18n()
  const { user } = useAuth()
  const [search, setSearch] = useState('')
  const [stage, setStage] = useState('')
  const [page, setPage] = useState(1)
  const stages = useApi('/cases/stages/')
  const { data, error, loading, reload } = useApi('/cases/', { params: { search, stage, page } })

  return (
    <>
      <PageHeader title={t('cases.title')} subtitle={t('cases.subtitle')}
        actions={user.permissions.register_case && <Link to="/app/cases/new" className="inline-flex min-h-[44px] items-center gap-2 rounded-lg bg-navy px-4 font-semibold text-white hover:bg-deep"><Icon name="plus" className="h-4 w-4" />{t('cases.new')}</Link>} />
      <Card>
        <div className="flex flex-wrap gap-3 border-b border-line p-4">
          <div className="min-w-[200px] flex-1"><Input type="search" placeholder={t('cases.searchPlaceholder')} aria-label={t('common.search')} value={search} onChange={(e) => { setSearch(e.target.value); setPage(1) }} /></div>
          <div className="w-full sm:w-64">
            <Select aria-label={t('cases.stage')} value={stage} onChange={(e) => { setStage(e.target.value); setPage(1) }}>
              <option value="">{t('cases.allStages')}</option>
              {stages.data?.map((s) => <option key={s.code} value={s.code}>{t(`stage.${s.code}`)}</option>)}
            </Select>
          </div>
        </div>
        {loading && !data ? <Loading /> : error ? <div className="p-4"><ErrorState error={error} onRetry={reload} /></div>
          : data.results.length === 0 ? <EmptyState icon="folder" title={t('cases.empty')}>{t('cases.emptyHint')}</EmptyState> : (
            <>
              <Table head={[t('cases.reference'), t('cases.child'), t('cases.category'), t('cases.stage'), t('cases.lead'), t('cases.reported')]}>
                {data.results.map((c) => (
                  <tr key={c.id} className="hover:bg-ivory/70">
                    <td className="px-4 py-3"><Link className="font-mono font-semibold text-navy hover:underline" to={`/app/cases/${c.id}`}>{c.reference}</Link>
                      {c.immediate_risk && <span className="ml-2"><Badge tone="danger">{t('cases.risk')}</Badge></span>}</td>
                    <td className="px-4 py-3">{c.child_pseudonym}<span className="block text-xs text-muted">{t(`age.${c.age_range}`)}</span></td>
                    <td className="px-4 py-3">{t(`incident.${c.incident_category}`)}</td>
                    <td className="px-4 py-3"><Badge tone="info" icon={null}>{t(`stage.${c.stage.code}`)}</Badge></td>
                    <td className="px-4 py-3 text-muted">{c.is_lead ? t('cases.yourInstitution') : c.lead_institution.name}</td>
                    <td className="whitespace-nowrap px-4 py-3 text-muted">{fmtDate(c.date_reported, lang)}</td>
                  </tr>
                ))}
              </Table>
              <div className="flex items-center justify-between border-t border-line px-4 py-3 text-sm text-muted">
                <span>{t('common.totalCount', { n: data.count })}</span>
                <span className="flex gap-2">
                  <Button size="sm" variant="secondary" disabled={!data.previous} onClick={() => setPage((p) => p - 1)}>{t('common.previous')}</Button>
                  <Button size="sm" variant="secondary" disabled={!data.next} onClick={() => setPage((p) => p + 1)}>{t('common.next')}</Button>
                </span>
              </div>
            </>
          )}
      </Card>
    </>
  )
}

export function CaseNew() {
  const { t } = useI18n()
  const navigate = useNavigate()
  const officers = useApi('/cases/officers/')
  const [serverError, setServerError] = useState(null)
  const [duplicate, setDuplicate] = useState(null)
  const today = new Date().toISOString().slice(0, 10)
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm({
    defaultValues: { date_reported: today, preferred_language: 'en', region: 'CENTRAL', referral_needs: [], immediate_risk: false },
  })

  const submit = async (values, confirm = false) => {
    setServerError(null)
    const body = { ...values, confirm_not_duplicate: confirm }
    if (!body.assigned_officer_id) delete body.assigned_officer_id
    try {
      const r = await api.post('/cases/', body)
      navigate(`/app/cases/${r.data.id}?created=1`)
    } catch (e) {
      const d = describeError(e, t)
      if (d.fields.duplicate_warning) setDuplicate({ values, message: d.fields.duplicate_warning })
      else setServerError(d)
    }
  }

  const err = (name) => errors[name] ? t('validation.required') : serverError?.fields?.[name]

  return (
    <>
      <PageHeader title={t('caseNew.title')} subtitle={t('caseNew.subtitle')}
        back={<Link to="/app/cases" className="mb-2 inline-flex items-center gap-1 text-sm font-semibold text-teal"><Icon name="arrowLeft" className="h-4 w-4" />{t('nav.cases')}</Link>} />
      <form onSubmit={handleSubmit((v) => submit(v))} noValidate className="grid gap-6 lg:grid-cols-[1fr_20rem]">
        <div className="space-y-6">
          <Card className="space-y-4 p-5">
            <h2 className="font-semibold text-navy">{t('caseNew.childSection')}</h2>
            <Alert tone="bronze">{t('caseNew.minimisation')}</Alert>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label={t('caseNew.pseudonym')} hint={t('caseNew.pseudonymHint')} required error={err('child_pseudonym')}>
                {(a) => <Input {...a} placeholder="Demo Child C" {...register('child_pseudonym', { required: true, maxLength: 60 })} />}
              </Field>
              <Field label={t('caseNew.ageRange')} required error={err('age_range')}>
                {(a) => <Select {...a} {...register('age_range', { required: true })}><option value="">{t('common.choose')}</option>{AGE_RANGES.map((x) => <option key={x} value={x}>{t(`age.${x}`)}</option>)}</Select>}
              </Field>
              <Field label={t('caseNew.language')} required>
                {(a) => <Select {...a} {...register('preferred_language')}>{LANG_CODES.map((x) => <option key={x} value={x}>{t(`languages.${x}`)}</option>)}</Select>}
              </Field>
            </div>
          </Card>
          <Card className="space-y-4 p-5">
            <h2 className="font-semibold text-navy">{t('caseNew.reportSection')}</h2>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label={t('caseNew.dateReported')} required error={err('date_reported')}>
                {(a) => <Input {...a} type="date" max={today} {...register('date_reported', { required: true })} />}
              </Field>
              <Field label={t('caseNew.category')} required error={err('incident_category')}>
                {(a) => <Select {...a} {...register('incident_category', { required: true })}><option value="">{t('common.choose')}</option>{INCIDENT_CATEGORIES.map((x) => <option key={x} value={x}>{t(`incident.${x}`)}</option>)}</Select>}
              </Field>
              <Field label={t('caseNew.district')} required error={err('district')}>
                {(a) => <Input {...a} {...register('district', { required: true })} />}
              </Field>
              <Field label={t('caseNew.region')} required>
                {(a) => <Select {...a} {...register('region')}>{REGIONS.map((x) => <option key={x} value={x}>{t(`region.${x}`)}</option>)}</Select>}
              </Field>
              <Field label={t('caseNew.externalRef')} hint={t('caseNew.externalRefHint')} error={serverError?.fields?.external_reference}>
                {(a) => <Input {...a} {...register('external_reference')} />}
              </Field>
              <Field label={t('caseNew.assignedOfficer')} hint={t('caseNew.assignedOfficerHint')}>
                {(a) => <Select {...a} {...register('assigned_officer_id')}><option value="">{t('caseNew.me')}</option>{officers.data?.map((o) => <option key={o.id} value={o.id}>{o.full_name}</option>)}</Select>}
              </Field>
            </div>
          </Card>
          <Card className="space-y-4 p-5">
            <h2 className="flex items-center gap-2 font-semibold text-navy"><Icon name="shield" className="h-4 w-4 text-bronze" />{t('caseNew.restrictedSection')}</h2>
            <p className="text-sm text-muted">{t('caseNew.restrictedHint')}</p>
            <Checkbox label={t('caseNew.immediateRisk')} hint={t('caseNew.immediateRiskHint')} {...register('immediate_risk')} />
            <Field label={t('caseNew.protectionConcerns')}>{(a) => <Textarea {...a} maxLength={1000} {...register('protection_concerns')} />}</Field>
            <Field label={t('caseNew.locationDetail')}>{(a) => <Input {...a} maxLength={300} {...register('location_detail')} />}</Field>
          </Card>
        </div>
        <div className="space-y-4">
          <Card className="space-y-3 p-5 lg:sticky lg:top-24">
            <h2 className="font-semibold text-navy">{t('caseNew.needsSection')}</h2>
            <p className="text-sm text-muted">{t('caseNew.needsHint')}</p>
            {REFERRAL_NEEDS.map((n) => <Checkbox key={n} value={n} label={t(`referralCategory.${n}`)} {...register('referral_needs')} />)}
            {serverError && <Alert tone="danger">{serverError.message}</Alert>}
            <Button type="submit" size="lg" className="w-full" busy={isSubmitting}>{t('caseNew.submit')}</Button>
          </Card>
        </div>
      </form>
      {duplicate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-navy/40 p-4">
          <Card className="max-w-md space-y-4 p-6" role="alertdialog" aria-modal="true">
            <h2 className="text-lg font-semibold text-navy">{t('caseNew.duplicateTitle')}</h2>
            <Alert tone="warn">{duplicate.message}</Alert>
            <div className="flex justify-end gap-2">
              <Button variant="secondary" onClick={() => setDuplicate(null)}>{t('common.cancel')}</Button>
              <Button onClick={() => { const v = duplicate.values; setDuplicate(null); submit(v, true) }}>{t('caseNew.confirmNotDuplicate')}</Button>
            </div>
          </Card>
        </div>
      )}
    </>
  )
}
