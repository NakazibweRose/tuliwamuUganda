import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { api, describeError } from '../../api/client'
import { useAuth } from '../../auth/AuthContext'
import { LanguageSelect } from '../../components/common'
import { Alert, Button, Card, CardHeader, Checkbox, ErrorState, Field, Input, Loading, PageHeader, Select } from '../../components/ui'
import { useApi } from '../../hooks/useApi'
import { useI18n } from '../../i18n'

function Preferences() {
  const { t } = useI18n()
  const { data, error, loading, setData } = useApi('/notifications/preferences/')
  const [msg, setMsg] = useState(null)
  const { register, handleSubmit, watch, formState: { isSubmitting } } = useForm({ values: data ? { ...data, safe_phone: '' } : undefined })
  const channel = watch('preferred_channel')
  if (loading) return <Loading />
  if (error) return <div className="p-5"><ErrorState error={error} /></div>
  const save = async (v) => {
    setMsg(null)
    const body = { preferred_channel: v.preferred_channel, sms_consent: v.sms_consent, quiet_hours_start: Number(v.quiet_hours_start), quiet_hours_end: Number(v.quiet_hours_end) }
    if (v.safe_phone) body.safe_phone = v.safe_phone
    try { const r = await api.patch('/notifications/preferences/', body); setData(r.data); setMsg({ tone: 'success', text: t('settings.saved') }) }
    catch (e) { const d = describeError(e, t); setMsg({ tone: 'danger', text: Object.values(d.fields)[0] || d.message }) }
  }
  return (
    <form onSubmit={handleSubmit(save)} className="space-y-4 p-5">
      <Alert tone="bronze">{t('settings.discreetNote')}</Alert>
      <Field label={t('settings.channel')}>{(a) => <Select {...a} {...register('preferred_channel')}>
        {['IN_APP', 'SMS', 'EMAIL'].map((c) => <option key={c} value={c}>{t(`channel.${c}`)}</option>)}</Select>}</Field>
      {channel === 'SMS' && (
        <div className="space-y-4 rounded-xl border border-line p-4">
          <Checkbox label={t('settings.smsConsent')} hint={t('settings.smsConsentHint')} {...register('sms_consent')} />
          <Field label={t('settings.safePhone')} hint={data.safe_phone_set ? t('settings.safePhoneSet') : t('settings.safePhoneHint')}>
            {(a) => <Input {...a} type="tel" inputMode="tel" placeholder="07XXXXXXXX" {...register('safe_phone')} />}
          </Field>
          <div className="grid grid-cols-2 gap-4">
            <Field label={t('settings.quietFrom')}>{(a) => <Input {...a} type="number" min={0} max={23} {...register('quiet_hours_start')} />}</Field>
            <Field label={t('settings.quietTo')}>{(a) => <Input {...a} type="number" min={0} max={23} {...register('quiet_hours_end')} />}</Field>
          </div>
          {data.consent_reference && <p className="text-xs text-muted">{t('settings.consentRef')}: {data.consent_reference}</p>}
        </div>
      )}
      {msg && <Alert tone={msg.tone}>{msg.text}</Alert>}
      <Button type="submit" busy={isSubmitting}>{t('common.save')}</Button>
    </form>
  )
}

function PasswordForm() {
  const { t } = useI18n()
  const [msg, setMsg] = useState(null)
  const { register, handleSubmit, reset, formState: { isSubmitting } } = useForm()
  const save = async (v) => {
    setMsg(null)
    try { await api.post('/auth/change-password/', v); reset(); setMsg({ tone: 'success', text: t('settings.passwordChanged') }) }
    catch (e) { const d = describeError(e, t); setMsg({ tone: 'danger', text: Object.values(d.fields)[0] || d.message }) }
  }
  return (
    <form onSubmit={handleSubmit(save)} className="space-y-4 p-5">
      <Field label={t('settings.currentPassword')}>{(a) => <Input {...a} type="password" autoComplete="current-password" {...register('current_password', { required: true })} />}</Field>
      <Field label={t('settings.newPassword')} hint={t('settings.passwordHint')}>{(a) => <Input {...a} type="password" autoComplete="new-password" {...register('new_password', { required: true })} />}</Field>
      {msg && <Alert tone={msg.tone}>{msg.text}</Alert>}
      <Button type="submit" busy={isSubmitting}>{t('settings.changePassword')}</Button>
    </form>
  )
}

export default function Settings() {
  const { t } = useI18n()
  const { user } = useAuth()
  return (
    <>
      <PageHeader title={t('settings.title')} subtitle={user.full_name} />
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="space-y-6">
          <Card>
            <CardHeader title={t('settings.languageTitle')} subtitle={t('settings.languageHint')} />
            <div className="p-5"><LanguageSelect onChange={(l) => api.patch('/auth/me/', { preferred_language: l }).catch(() => {})} /></div>
          </Card>
          <Card><CardHeader title={t('settings.notificationsTitle')} /><Preferences /></Card>
        </div>
        <Card className="self-start"><CardHeader title={t('settings.passwordTitle')} /><PasswordForm /></Card>
      </div>
    </>
  )
}
