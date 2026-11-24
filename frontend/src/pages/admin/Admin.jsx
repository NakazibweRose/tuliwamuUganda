import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { api, describeError } from '../../api/client'
import { Alert, Badge, Button, Card, Checkbox, EmptyState, ErrorState, Field, Input, Loading, Modal, PageHeader, Select, Table, Textarea } from '../../components/ui'
import { useApi } from '../../hooks/useApi'
import { useI18n } from '../../i18n'
import { fmtDateTime } from '../../lib/format'
import { INSTITUTION_TYPES, LANG_CODES, REGIONS, ROLES } from '../../lib/labels'

function errText(e, t) { const d = describeError(e, t); return Object.entries(d.fields).map(([k, v]) => `${k}: ${v}`).join(' ') || d.message }

export function Users() {
  const { t } = useI18n()
  const [search, setSearch] = useState('')
  const [role, setRole] = useState('')
  const { data, error, loading, reload } = useApi('/admin/users/', { params: { search, role, page_size: 100 } })
  const insts = useApi('/institutions/', { params: { page_size: 100 } })
  const [editing, setEditing] = useState(null)
  const [err, setErr] = useState(null)
  const { register, handleSubmit, reset, formState: { isSubmitting } } = useForm()
  const open = (u) => {
    setErr(null)
    setEditing(u || {})
    reset(u ? { ...u, institution_id: u.institution?.id || '', password: '' } : { role: 'POLICE', preferred_language: 'en', is_active: true })
  }
  const save = async (v) => {
    setErr(null)
    const body = { ...v }
    if (!body.password) delete body.password
    if (!body.institution_id) delete body.institution_id
    try {
      if (editing.id) await api.patch(`/admin/users/${editing.id}/`, body)
      else await api.post('/admin/users/', body)
      setEditing(null); reload()
    } catch (e) { setErr(errText(e, t)) }
  }
  return (
    <>
      <PageHeader title={t('admin.usersTitle')} subtitle={t('admin.usersSubtitle')} actions={<Button icon="plus" onClick={() => open(null)}>{t('admin.newUser')}</Button>} />
      <Card>
        <div className="flex flex-wrap gap-3 border-b border-line p-4">
          <div className="min-w-[200px] flex-1"><Input type="search" aria-label={t('common.search')} placeholder={t('common.search')} value={search} onChange={(e) => setSearch(e.target.value)} /></div>
          <div className="w-full sm:w-56"><Select aria-label={t('admin.role')} value={role} onChange={(e) => setRole(e.target.value)}><option value="">{t('admin.allRoles')}</option>{ROLES.map((r) => <option key={r} value={r}>{t(`roles.${r}`)}</option>)}</Select></div>
        </div>
        {loading && !data ? <Loading /> : error ? <div className="p-4"><ErrorState error={error} /></div> : (
          <Table head={[t('admin.username'), t('admin.name'), t('admin.role'), t('admin.institution'), t('admin.lastLogin'), t('admin.status'), '']}>
            {data.results.map((u) => (
              <tr key={u.id}>
                <td className="px-4 py-3 font-mono text-xs">{u.username}</td>
                <td className="px-4 py-3">{u.full_name}</td>
                <td className="px-4 py-3">{t(`roles.${u.role}`)}{u.is_supervisor && <span className="ml-1"><Badge tone="bronze" icon={null}>{t('admin.supervisor')}</Badge></span>}</td>
                <td className="px-4 py-3 text-muted">{u.institution?.name || '—'}</td>
                <td className="whitespace-nowrap px-4 py-3 text-muted">{fmtDateTime(u.last_login)}</td>
                <td className="px-4 py-3"><Badge tone={u.is_active ? 'success' : 'neutral'}>{u.is_active ? t('admin.active') : t('admin.inactive')}</Badge></td>
                <td className="px-4 py-3"><Button size="sm" variant="secondary" onClick={() => open(u)}>{t('common.edit')}</Button></td>
              </tr>
            ))}
          </Table>
        )}
      </Card>
      <Modal open={!!editing} onClose={() => setEditing(null)} title={editing?.id ? t('admin.editUser') : t('admin.newUser')} wide>
        <form onSubmit={handleSubmit(save)} className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label={t('admin.username')} required>{(a) => <Input {...a} disabled={!!editing?.id} {...register('username', { required: true })} />}</Field>
            <Field label={t('admin.name')}>{(a) => <Input {...a} {...register('full_name')} />}</Field>
            <Field label={t('admin.email')}>{(a) => <Input {...a} type="email" {...register('email')} />}</Field>
            <Field label={t('admin.role')}>{(a) => <Select {...a} {...register('role')}>{ROLES.map((r) => <option key={r} value={r}>{t(`roles.${r}`)}</option>)}</Select>}</Field>
            <Field label={t('admin.institution')} hint={t('admin.institutionHint')}>{(a) => <Select {...a} {...register('institution_id')}><option value="">—</option>{insts.data?.results?.map((i) => <option key={i.id} value={i.id}>{i.name}</option>)}</Select>}</Field>
            <Field label={t('admin.language')}>{(a) => <Select {...a} {...register('preferred_language')}>{LANG_CODES.map((l) => <option key={l} value={l}>{t(`languages.${l}`)}</option>)}</Select>}</Field>
            <Field label={editing?.id ? t('admin.resetPassword') : t('admin.initialPassword')} hint={t('settings.passwordHint')}>{(a) => <Input {...a} type="password" autoComplete="new-password" {...register('password')} />}</Field>
          </div>
          <Checkbox label={t('admin.supervisorLabel')} hint={t('admin.supervisorHint')} {...register('is_supervisor')} />
          <Checkbox label={t('admin.active')} {...register('is_active')} />
          <Alert tone="info">{t('admin.noCaseAccess')}</Alert>
          {err && <Alert tone="danger">{err}</Alert>}
          <div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={() => setEditing(null)}>{t('common.cancel')}</Button><Button type="submit" busy={isSubmitting}>{t('common.save')}</Button></div>
        </form>
      </Modal>
    </>
  )
}

export function Institutions() {
  const { t } = useI18n()
  const { data, error, loading, reload } = useApi('/institutions/', { params: { page_size: 100 } })
  const [editing, setEditing] = useState(null)
  const [err, setErr] = useState(null)
  const { register, handleSubmit, reset, formState: { isSubmitting } } = useForm()
  const open = (i) => { setErr(null); setEditing(i || {}); reset(i || { type: 'POLICE', region: 'CENTRAL', is_active: true, is_demo: true }) }
  const save = async (v) => {
    try { if (editing.id) await api.patch(`/institutions/${editing.id}/`, v); else await api.post('/institutions/', v); setEditing(null); reload() } catch (e) { setErr(errText(e, t)) }
  }
  return (
    <>
      <PageHeader title={t('admin.institutionsTitle')} subtitle={t('admin.institutionsSubtitle')} actions={<Button icon="plus" onClick={() => open(null)}>{t('admin.newInstitution')}</Button>} />
      <Card>
        {loading ? <Loading /> : error ? <div className="p-4"><ErrorState error={error} /></div> : (
          <Table head={[t('admin.name'), t('admin.type'), t('caseNew.district'), t('caseNew.region'), t('admin.members'), t('admin.status'), '']}>
            {data.results.map((i) => (
              <tr key={i.id}>
                <td className="px-4 py-3 font-semibold text-navy">{i.name}{i.is_demo && <span className="ml-2"><Badge tone="bronze" icon={null}>{t('admin.demo')}</Badge></span>}</td>
                <td className="px-4 py-3">{t(`institutionType.${i.type}`)}</td>
                <td className="px-4 py-3">{i.district}</td>
                <td className="px-4 py-3">{t(`region.${i.region}`)}</td>
                <td className="px-4 py-3 tabular-nums">{i.member_count}</td>
                <td className="px-4 py-3"><Badge tone={i.is_active ? 'success' : 'neutral'}>{i.is_active ? t('admin.active') : t('admin.inactive')}</Badge></td>
                <td className="px-4 py-3"><Button size="sm" variant="secondary" onClick={() => open(i)}>{t('common.edit')}</Button></td>
              </tr>
            ))}
          </Table>
        )}
      </Card>
      <Modal open={!!editing} onClose={() => setEditing(null)} title={editing?.id ? t('admin.editInstitution') : t('admin.newInstitution')}>
        <form onSubmit={handleSubmit(save)} className="space-y-4">
          <Field label={t('admin.name')} required>{(a) => <Input {...a} {...register('name', { required: true })} />}</Field>
          <div className="grid grid-cols-2 gap-4">
            <Field label={t('admin.type')}>{(a) => <Select {...a} {...register('type')}>{INSTITUTION_TYPES.map((x) => <option key={x} value={x}>{t(`institutionType.${x}`)}</option>)}</Select>}</Field>
            <Field label={t('caseNew.region')}>{(a) => <Select {...a} {...register('region')}>{REGIONS.map((x) => <option key={x} value={x}>{t(`region.${x}`)}</option>)}</Select>}</Field>
          </div>
          <Field label={t('caseNew.district')} required>{(a) => <Input {...a} {...register('district', { required: true })} />}</Field>
          <Field label={t('admin.publicContact')} hint={t('admin.publicContactHint')}>{(a) => <Input {...a} {...register('public_contact')} />}</Field>
          <Checkbox label={t('admin.active')} {...register('is_active')} />
          {err && <Alert tone="danger">{err}</Alert>}
          <div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={() => setEditing(null)}>{t('common.cancel')}</Button><Button type="submit" busy={isSubmitting}>{t('common.save')}</Button></div>
        </form>
      </Modal>
    </>
  )
}

export function Services() {
  const { t } = useI18n()
  const { data, error, loading, reload } = useApi('/support-services/', { params: { page_size: 100 } })
  const insts = useApi('/institutions/', { params: { page_size: 100 } })
  const [editing, setEditing] = useState(null)
  const [err, setErr] = useState(null)
  const { register, handleSubmit, reset, formState: { isSubmitting } } = useForm()
  const cats = ['MEDICAL', 'PSYCHOSOCIAL', 'LEGAL_AID', 'SHELTER', 'PROBATION', 'HELPLINE']
  const open = (s) => { setErr(null); setEditing(s || {}); reset(s ? { ...s, languages: s.languages.join(', '), districts: s.districts.join(', ') } : { category: 'PSYCHOSOCIAL', is_active: true, is_free: true }) }
  const split = (v) => (v || '').split(',').map((x) => x.trim()).filter(Boolean)
  const save = async (v) => {
    const body = { ...v, languages: split(v.languages), districts: split(v.districts) }
    try { if (editing.id) await api.patch(`/support-services/${editing.id}/`, body); else await api.post('/support-services/', body); setEditing(null); reload() } catch (e) { setErr(errText(e, t)) }
  }
  return (
    <>
      <PageHeader title={t('admin.servicesTitle')} subtitle={t('admin.servicesSubtitle')} actions={<Button icon="plus" onClick={() => open(null)}>{t('admin.newService')}</Button>} />
      <Card>
        {loading ? <Loading /> : error ? <div className="p-4"><ErrorState error={error} /></div> : data.results.length === 0 ? <EmptyState title={t('admin.noServices')} /> : (
          <Table head={[t('admin.name'), t('admin.category'), t('admin.institution'), t('admin.contact'), t('admin.status'), '']}>
            {data.results.map((s) => (
              <tr key={s.id}>
                <td className="px-4 py-3"><p className="font-semibold text-navy">{s.name}</p><p className="text-xs text-muted">{s.description}</p></td>
                <td className="px-4 py-3">{t(`serviceCategory.${s.category}`)}</td>
                <td className="px-4 py-3 text-muted">{s.institution_name}</td>
                <td className="px-4 py-3">{s.public_contact}</td>
                <td className="px-4 py-3"><Badge tone={s.is_active ? 'success' : 'neutral'}>{s.is_active ? t('admin.active') : t('admin.inactive')}</Badge></td>
                <td className="px-4 py-3"><Button size="sm" variant="secondary" onClick={() => open(s)}>{t('common.edit')}</Button></td>
              </tr>
            ))}
          </Table>
        )}
      </Card>
      <Modal open={!!editing} onClose={() => setEditing(null)} title={editing?.id ? t('admin.editService') : t('admin.newService')} wide>
        <form onSubmit={handleSubmit(save)} className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label={t('admin.name')} required>{(a) => <Input {...a} {...register('name', { required: true })} />}</Field>
            <Field label={t('admin.category')}>{(a) => <Select {...a} {...register('category')}>{cats.map((c) => <option key={c} value={c}>{t(`serviceCategory.${c}`)}</option>)}</Select>}</Field>
            <Field label={t('admin.institution')} required>{(a) => <Select {...a} {...register('institution', { required: true })}><option value="">—</option>{insts.data?.results?.map((i) => <option key={i.id} value={i.id}>{i.name}</option>)}</Select>}</Field>
            <Field label={t('admin.contact')}>{(a) => <Input {...a} {...register('public_contact')} />}</Field>
            <Field label={t('admin.hours')}>{(a) => <Input {...a} {...register('hours')} />}</Field>
            <Field label={t('admin.languagesCsv')}>{(a) => <Input {...a} {...register('languages')} />}</Field>
          </div>
          <Field label={t('admin.description')} required>{(a) => <Textarea {...a} maxLength={500} {...register('description', { required: true })} />}</Field>
          <Field label={t('admin.districtsCsv')}>{(a) => <Input {...a} {...register('districts')} />}</Field>
          <div className="flex gap-6"><Checkbox label={t('admin.free')} {...register('is_free')} /><Checkbox label={t('admin.active')} {...register('is_active')} /></div>
          {err && <Alert tone="danger">{err}</Alert>}
          <div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={() => setEditing(null)}>{t('common.cancel')}</Button><Button type="submit" busy={isSubmitting}>{t('common.save')}</Button></div>
        </form>
      </Modal>
    </>
  )
}

export function AuditLogs() {
  const { t, lang } = useI18n()
  const [security, setSecurity] = useState('')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const { data, error, loading } = useApi('/audit-logs/', { params: { is_security_event: security || undefined, search, page, page_size: 50 } })
  return (
    <>
      <PageHeader title={t('admin.auditTitle')} subtitle={t('admin.auditSubtitle')} />
      <Card>
        <div className="flex flex-wrap gap-3 border-b border-line p-4">
          <div className="min-w-[200px] flex-1"><Input type="search" aria-label={t('common.search')} placeholder={t('admin.auditSearch')} value={search} onChange={(e) => { setSearch(e.target.value); setPage(1) }} /></div>
          <div className="w-full sm:w-56"><Select aria-label={t('admin.filter')} value={security} onChange={(e) => { setSecurity(e.target.value); setPage(1) }}>
            <option value="">{t('admin.allEvents')}</option><option value="true">{t('admin.securityOnly')}</option></Select></div>
        </div>
        {loading && !data ? <Loading /> : error ? <div className="p-4"><ErrorState error={error} /></div> : (
          <>
            <Table head={[t('admin.when'), t('admin.actor'), t('admin.action'), t('admin.object'), t('admin.result')]}>
              {data.results.map((e) => (
                <tr key={e.id}>
                  <td className="whitespace-nowrap px-4 py-2.5 text-muted">{fmtDateTime(e.created_at, lang)}</td>
                  <td className="px-4 py-2.5">{e.actor || t('common.anonymous')}<span className="block text-xs text-muted">{e.actor_role && t(`roles.${e.actor_role}`)}{e.institution && ` · ${e.institution}`}</span></td>
                  <td className="px-4 py-2.5 font-mono text-xs">{e.action}{e.is_security_event && <span className="ml-1"><Badge tone="warn" icon="shield">{t('admin.security')}</Badge></span>}</td>
                  <td className="px-4 py-2.5 font-mono text-[11px] text-muted">{e.object_type} {e.object_id?.slice(0, 8)}</td>
                  <td className="px-4 py-2.5"><Badge tone={e.success ? 'success' : 'danger'}>{e.success ? t('common.ok') : t('common.denied')}</Badge></td>
                </tr>
              ))}
            </Table>
            <div className="flex items-center justify-between border-t border-line px-4 py-3 text-sm text-muted">
              <span>{t('common.totalCount', { n: data.count })}</span>
              <span className="flex gap-2"><Button size="sm" variant="secondary" disabled={!data.previous} onClick={() => setPage((p) => p - 1)}>{t('common.previous')}</Button><Button size="sm" variant="secondary" disabled={!data.next} onClick={() => setPage((p) => p + 1)}>{t('common.next')}</Button></span>
            </div>
          </>
        )}
      </Card>
    </>
  )
}
