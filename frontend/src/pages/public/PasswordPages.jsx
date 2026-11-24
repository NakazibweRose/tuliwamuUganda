import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useSearchParams } from 'react-router-dom'
import { api, describeError } from '../../api/client'
import { LanguageSelect, Logo } from '../../components/common'
import { Alert, Button, Card, Field, Input } from '../../components/ui'
import { useT } from '../../i18n'

function Shell({ title, children }) {
  const t = useT()
  return (
    <div className="flex min-h-screen flex-col bg-ivory px-4 py-6">
      <div className="mx-auto flex w-full max-w-md items-center justify-between"><Link to="/login"><Logo small /></Link><LanguageSelect compact /></div>
      <Card className="mx-auto my-auto w-full max-w-md p-6">
        <h1 className="font-serif text-2xl font-semibold text-navy">{title}</h1>
        <div className="mt-4">{children}</div>
        <Link to="/login" className="mt-6 inline-block text-sm font-semibold text-teal hover:underline">← {t('common.backToLogin')}</Link>
      </Card>
    </div>
  )
}

export function ForgotPassword() {
  const t = useT()
  const [done, setDone] = useState(null)
  const [error, setError] = useState(null)
  const { register, handleSubmit, formState: { isSubmitting, errors } } = useForm()
  const submit = async ({ email }) => {
    setError(null)
    try { setDone((await api.post('/auth/password-reset/', { email })).data.detail) } catch (e) { setError(describeError(e, t).message) }
  }
  return (
    <Shell title={t('recovery.title')}>
      <Alert tone="bronze">{t('recovery.beneficiaryNote')}</Alert>
      {done ? <div className="mt-4"><Alert tone="success">{done}</Alert></div> : (
        <form onSubmit={handleSubmit(submit)} className="mt-4 space-y-4" noValidate>
          <Field label={t('recovery.email')} error={errors.email && t('validation.email')}>
            {(a) => <Input {...a} type="email" autoComplete="email" {...register('email', { required: true, pattern: /@/ })} />}
          </Field>
          {error && <Alert tone="danger">{error}</Alert>}
          <Button type="submit" busy={isSubmitting} className="w-full">{t('recovery.send')}</Button>
        </form>
      )}
    </Shell>
  )
}

export function ResetPassword() {
  const t = useT()
  const [params] = useSearchParams()
  const [done, setDone] = useState(false)
  const [error, setError] = useState(null)
  const { register, handleSubmit, formState: { isSubmitting } } = useForm()
  const submit = async ({ new_password }) => {
    setError(null)
    try {
      await api.post('/auth/password-reset/confirm/', { uid: params.get('uid'), token: params.get('token'), new_password })
      setDone(true)
    } catch (e) { const d = describeError(e, t); setError(d.fields.new_password || d.message) }
  }
  return (
    <Shell title={t('recovery.resetTitle')}>
      {done ? <Alert tone="success">{t('recovery.resetDone')}</Alert> : (
        <form onSubmit={handleSubmit(submit)} className="space-y-4">
          <Field label={t('settings.newPassword')} hint={t('settings.passwordHint')}>
            {(a) => <Input {...a} type="password" autoComplete="new-password" {...register('new_password', { required: true })} />}
          </Field>
          {error && <Alert tone="danger">{error}</Alert>}
          <Button type="submit" busy={isSubmitting} className="w-full">{t('recovery.resetSubmit')}</Button>
        </form>
      )}
    </Shell>
  )
}

export function About() {
  const t = useT()
  return (
    <Shell title={t('about.title')}>
      <div className="space-y-3 text-sm text-ink">
        <p>{t('about.p1')}</p>
        <p>{t('about.p2')}</p>
        <Alert tone="danger" title={t('about.emergencyTitle')}>{t('about.emergency')}</Alert>
        <p>{t('about.p3')}</p>
        <p className="text-muted">{t('common.disclaimer')}</p>
      </div>
    </Shell>
  )
}
