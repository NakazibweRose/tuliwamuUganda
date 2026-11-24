import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate } from 'react-router-dom'
import { describeError } from '../../api/client'
import { useAuth } from '../../auth/AuthContext'
import { DraftTranslationNotice, LanguageSelect, Logo, OfflineBanner, PrototypeDisclaimer } from '../../components/common'
import { Alert, Button, Field, Icon, Input } from '../../components/ui'
import { useT } from '../../i18n'

export const DEMO_ACCOUNTS = [
  ['police.officer', 'POLICE'], ['police.supervisor', 'POLICE'], ['medical.officer', 'MEDICAL'], ['forensic.officer', 'FORENSIC'],
  ['prosecutor', 'PROSECUTOR'], ['court.registry', 'COURT'], ['probation.officer', 'PROBATION'], ['legalaid.officer', 'LEGAL_AID'],
  ['complainant.demo', 'COMPLAINANT'], ['caregiver.demo', 'CAREGIVER'], ['complainant.two', 'COMPLAINANT'], ['admin', 'ADMIN'], ['gulu.officer', 'POLICE'],
]

export function homeFor(user) {
  return user.permissions?.beneficiary_portal ? '/me' : '/app'
}

export default function Login() {
  const t = useT()
  const { login, notice } = useAuth()
  const navigate = useNavigate()
  const [error, setError] = useState(null)
  const { register, handleSubmit, setValue, formState: { errors, isSubmitting } } = useForm()

  const onSubmit = async ({ username, password }) => {
    setError(null)
    try {
      const user = await login(username.trim(), password)
      navigate(homeFor(user), { replace: true })
    } catch (e) {
      setError(describeError(e, t).message)
    }
  }

  return (
    <div className="min-h-screen bg-ivory">
      <OfflineBanner />
      <DraftTranslationNotice />
      <div className="mx-auto grid min-h-screen max-w-6xl lg:grid-cols-[1.05fr_1fr]">
        <section className="relative hidden overflow-hidden bg-navy p-12 text-white lg:flex lg:flex-col">
          <Logo light />
          <div className="mt-auto max-w-md">
            <p className="text-sm font-semibold uppercase tracking-wider text-bronze">{t('login.kicker')}</p>
            <h1 className="mt-3 font-serif text-4xl font-semibold leading-tight">{t('login.heroTitle')}</h1>
            <p className="mt-4 text-white/75">{t('login.heroBody')}</p>
            <ul className="mt-8 space-y-3 text-sm text-white/80">
              {['q1', 'q2', 'q3', 'q4', 'q5'].map((q) => (
                <li key={q} className="flex gap-3"><Icon name="check" className="mt-0.5 h-4 w-4 shrink-0 text-bronze" />{t(`login.${q}`)}</li>
              ))}
            </ul>
          </div>
          <svg className="pointer-events-none absolute -right-24 -top-24 h-96 w-96 text-white/[0.04]" viewBox="0 0 100 100" aria-hidden="true"><circle cx="50" cy="50" r="50" fill="currentColor" /></svg>
        </section>

        <section className="flex flex-col px-5 py-8 sm:px-10">
          <div className="flex items-center justify-between">
            <span className="lg:hidden"><Logo small /></span>
            <span className="hidden lg:block" />
            <LanguageSelect />
          </div>
          <div className="mx-auto my-auto w-full max-w-sm py-10">
            <h2 className="font-serif text-3xl font-semibold text-navy">{t('login.title')}</h2>
            <p className="mt-2 text-muted">{t('login.subtitle')}</p>
            {notice && <div className="mt-5"><Alert tone="info">{t(`login.notice.${notice}`)}</Alert></div>}
            <form onSubmit={handleSubmit(onSubmit)} className="mt-6 space-y-4" noValidate>
              <Field label={t('login.username')} error={errors.username && t('validation.required')}>
                {(a) => <Input {...a} autoComplete="username" autoCapitalize="none" {...register('username', { required: true })} />}
              </Field>
              <Field label={t('login.password')} error={errors.password && t('validation.required')}>
                {(a) => <Input {...a} type="password" autoComplete="current-password" {...register('password', { required: true })} />}
              </Field>
              {error && <Alert tone="danger">{error}</Alert>}
              <Button type="submit" className="w-full" size="lg" busy={isSubmitting}>{t('login.submit')}</Button>
            </form>
            <div className="mt-4 flex justify-between text-sm">
              <Link to="/forgot-password" className="font-semibold text-teal hover:underline">{t('login.forgot')}</Link>
              <Link to="/about" className="font-semibold text-teal hover:underline">{t('login.safeguarding')}</Link>
            </div>

            <details className="mt-8 rounded-xl border border-line bg-white p-4 text-sm">
              <summary className="cursor-pointer font-semibold text-navy">{t('login.demoTitle')}</summary>
              <p className="mt-2 text-muted">{t('login.demoBody')} <code className="rounded bg-ivory px-1.5 py-0.5 font-mono text-ink">Tuliwamu#Demo2026</code></p>
              <div className="mt-3 grid grid-cols-2 gap-1.5">
                {DEMO_ACCOUNTS.map(([u, role]) => (
                  <button key={u} type="button" onClick={() => { setValue('username', u); setValue('password', 'Tuliwamu#Demo2026') }}
                    className="rounded-lg border border-line px-2 py-1.5 text-left hover:border-teal hover:bg-teal-50">
                    <span className="block truncate font-mono text-xs text-ink">{u}</span>
                    <span className="block truncate text-[11px] text-muted">{t(`roles.${role}`)}</span>
                  </button>
                ))}
              </div>
            </details>
            <PrototypeDisclaimer className="mt-6" />
          </div>
        </section>
      </div>
    </div>
  )
}
