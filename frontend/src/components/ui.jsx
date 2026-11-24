import { useEffect, useId, useRef } from 'react'
import { useT } from '../i18n'

/* ---------- Icons (inline, tiny, no icon library to keep bundles small) ---------- */
const paths = {
  home: 'M3 11l9-7 9 7v9a1 1 0 01-1 1h-5v-6H9v6H4a1 1 0 01-1-1v-9z',
  folder: 'M3 6a2 2 0 012-2h4l2 2h8a2 2 0 012 2v10a2 2 0 01-2 2H5a2 2 0 01-2-2V6z',
  send: 'M4 12l16-8-6 16-2.5-6.5L4 12z',
  calendar: 'M7 3v3M17 3v3M4 8h16M5 5h14a1 1 0 011 1v14a1 1 0 01-1 1H5a1 1 0 01-1-1V6a1 1 0 011-1z',
  bell: 'M6 16V11a6 6 0 1112 0v5l1.5 2h-15L6 16zM10 20a2 2 0 004 0',
  chart: 'M4 20h16M7 16V10M12 16V6M17 16v-4',
  users: 'M16 19v-1a4 4 0 00-4-4H7a4 4 0 00-4 4v1M9.5 10a3.5 3.5 0 100-7 3.5 3.5 0 000 7zM21 19v-1a4 4 0 00-3-3.9M15 3.1a3.5 3.5 0 010 6.8',
  shield: 'M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6l8-3z',
  list: 'M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01',
  check: 'M5 13l4 4L19 7',
  clock: 'M12 7v5l3 2M12 21a9 9 0 110-18 9 9 0 010 18z',
  alert: 'M12 9v4M12 17h.01M10.3 3.9L2.4 18a2 2 0 001.7 3h15.8a2 2 0 001.7-3L13.7 3.9a2 2 0 00-3.4 0z',
  x: 'M6 6l12 12M18 6L6 18',
  phone: 'M5 4h4l2 5-2.5 1.5a11 11 0 005 5L15 13l5 2v4a2 2 0 01-2 2A16 16 0 013 6a2 2 0 012-2z',
  help: 'M9.1 9a3 3 0 015.8 1c0 2-3 3-3 3M12 17h.01M12 21a9 9 0 110-18 9 9 0 010 18z',
  settings: 'M12 15a3 3 0 100-6 3 3 0 000 6zM19.4 15a1.7 1.7 0 00.3 1.8l.1.1a2 2 0 11-2.8 2.8l-.1-.1a1.7 1.7 0 00-1.8-.3 1.7 1.7 0 00-1 1.5V21a2 2 0 11-4 0v-.1a1.7 1.7 0 00-1.1-1.5 1.7 1.7 0 00-1.8.3l-.1.1a2 2 0 11-2.8-2.8l.1-.1a1.7 1.7 0 00.3-1.8 1.7 1.7 0 00-1.5-1H3a2 2 0 110-4h.1a1.7 1.7 0 001.5-1.1 1.7 1.7 0 00-.3-1.8l-.1-.1a2 2 0 112.8-2.8l.1.1a1.7 1.7 0 001.8.3H9a1.7 1.7 0 001-1.5V3a2 2 0 114 0v.1a1.7 1.7 0 001 1.5 1.7 1.7 0 001.8-.3l.1-.1a2 2 0 112.8 2.8l-.1.1a1.7 1.7 0 00-.3 1.8V9a1.7 1.7 0 001.5 1H21a2 2 0 110 4h-.1a1.7 1.7 0 00-1.5 1z',
  logout: 'M15 4h3a2 2 0 012 2v12a2 2 0 01-2 2h-3M10 17l5-5-5-5M15 12H3',
  inbox: 'M4 13h4l2 3h4l2-3h4M5 5h14l2 8v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6l2-8z',
  phoneSim: 'M8 2h8a2 2 0 012 2v16a2 2 0 01-2 2H8a2 2 0 01-2-2V4a2 2 0 012-2zM11 18h2',
  msg: 'M4 5h16v11H8l-4 4V5z',
  file: 'M7 3h7l5 5v12a1 1 0 01-1 1H7a1 1 0 01-1-1V4a1 1 0 011-1zM14 3v5h5',
  plus: 'M12 5v14M5 12h14',
  arrowRight: 'M5 12h14M13 6l6 6-6 6',
  arrowLeft: 'M19 12H5M11 6l-6 6 6 6',
  menu: 'M4 6h16M4 12h16M4 18h16',
  globe: 'M12 21a9 9 0 100-18 9 9 0 000 18zM3 12h18M12 3c2.5 2.5 3.5 5.5 3.5 9s-1 6.5-3.5 9c-2.5-2.5-3.5-5.5-3.5-9S9.5 5.5 12 3z',
  heart: 'M12 20s-7-4.5-7-10a4 4 0 017-2.6A4 4 0 0119 10c0 5.5-7 10-7 10z',
  eye: 'M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12zM12 15a3 3 0 100-6 3 3 0 000 6z',
}

export function Icon({ name, className = 'h-5 w-5', title }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"
      className={className} aria-hidden={title ? undefined : true} role={title ? 'img' : undefined}>
      {title && <title>{title}</title>}
      <path d={paths[name] || paths.file} />
    </svg>
  )
}

/* ---------- Buttons ---------- */
const variants = {
  primary: 'bg-navy text-white hover:bg-deep focus-visible:ring-navy',
  teal: 'bg-teal text-white hover:bg-teal-700 focus-visible:ring-teal',
  secondary: 'bg-white text-ink border border-line hover:bg-ivory focus-visible:ring-teal',
  ghost: 'text-deep hover:bg-teal-50 focus-visible:ring-teal',
  danger: 'bg-danger text-white hover:bg-danger-700 focus-visible:ring-danger',
}

export function Button({ variant = 'primary', size = 'md', busy, icon, children, className = '', ...props }) {
  const sizes = { sm: 'min-h-[36px] px-3 text-sm', md: 'min-h-[44px] px-4', lg: 'min-h-[52px] px-6 text-lg' }
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded-lg font-semibold transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60 ${variants[variant]} ${sizes[size]} ${className}`}
      disabled={busy || props.disabled}
      aria-busy={busy || undefined}
      {...props}
    >
      {busy ? <Spinner className="h-4 w-4" /> : icon ? <Icon name={icon} className="h-4 w-4" /> : null}
      {children}
    </button>
  )
}

export function Spinner({ className = 'h-5 w-5' }) {
  return (
    <svg className={`animate-spin ${className}`} viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="3" fill="none" opacity="0.25" />
      <path d="M21 12a9 9 0 00-9-9" stroke="currentColor" strokeWidth="3" fill="none" strokeLinecap="round" />
    </svg>
  )
}

/* ---------- Layout primitives ---------- */
// eslint-disable-next-line no-unused-vars -- `Tag` is used as a JSX element
export function Card({ children, className = '', as: Tag = 'section', ...props }) {
  return <Tag className={`rounded-xl border border-line bg-white shadow-card ${className}`} {...props}>{children}</Tag>
}

export function CardHeader({ title, subtitle, action }) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3 border-b border-line px-5 py-4">
      <div>
        <h2 className="text-base font-semibold text-navy">{title}</h2>
        {subtitle && <p className="mt-0.5 text-sm text-muted">{subtitle}</p>}
      </div>
      {action}
    </div>
  )
}

export function PageHeader({ title, subtitle, actions, back }) {
  return (
    <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0">
        {back}
        <h1 className="font-serif text-2xl font-semibold text-navy sm:text-[1.7rem]">{title}</h1>
        {subtitle && <p className="mt-1 max-w-2xl text-muted">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </header>
  )
}

/* ---------- Status badges: colour + icon + text (never colour alone) ---------- */
const tones = {
  neutral: 'bg-sage-50 text-ink border-line',
  info: 'bg-teal-50 text-teal-700 border-teal-100',
  success: 'bg-success-50 text-success-700 border-success/30',
  warn: 'bg-warn-50 text-warn-700 border-warn/30',
  danger: 'bg-danger-50 text-danger-700 border-danger/30',
  bronze: 'bg-bronze-50 text-[#7d6640] border-bronze/30',
}
const toneIcon = { success: 'check', warn: 'clock', danger: 'alert', info: 'arrowRight', neutral: null, bronze: 'shield' }

export function Badge({ tone = 'neutral', children, icon }) {
  const ic = icon === undefined ? toneIcon[tone] : icon
  return (
    <span className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full border px-2.5 py-0.5 text-xs font-semibold ${tones[tone]}`}>
      {ic && <Icon name={ic} className="h-3.5 w-3.5" />}
      {children}
    </span>
  )
}

const STATUS_TONES = {
  DRAFT: 'neutral', SENT: 'warn', ACKNOWLEDGED: 'info', IN_PROGRESS: 'info', COMPLETED: 'success', RETURNED: 'warn',
  DECLINED: 'danger', CANCELLED: 'neutral', SCHEDULED: 'info', RESCHEDULED: 'warn', MISSED: 'danger',
  PENDING: 'warn', DONE: 'success', ACTIVE: 'success', REVOKED: 'neutral', APPROVED: 'success', REJECTED: 'neutral',
  OPEN: 'warn', RESOLVED: 'success', CLOSED: 'neutral', NEW: 'warn', URGENT: 'danger', UNDER_REVIEW: 'info',
  REFERRED: 'success', CONVERTED: 'success', SIMULATED: 'bronze', SUBMITTED: 'info', DELIVERED: 'success', FAILED: 'danger',
  BLOCKED: 'neutral', DEFERRED: 'warn', QUEUED: 'neutral', UNVERIFIED: 'warn', CREDIBLE: 'danger', NOT_SUBSTANTIATED: 'neutral',
  DUPLICATE: 'neutral', MALICIOUS: 'neutral',
}

export function StatusBadge({ status, group = 'status' }) {
  const t = useT()
  return <Badge tone={STATUS_TONES[status] || 'neutral'}>{t(`${group}.${status}`)}</Badge>
}

export function PriorityBadge({ priority }) {
  const t = useT()
  const tone = priority === 'EMERGENCY' ? 'danger' : priority === 'URGENT' ? 'warn' : 'neutral'
  return <Badge tone={tone} icon={priority === 'ROUTINE' ? null : 'alert'}>{t(`priority.${priority}`)}</Badge>
}

/* ---------- States ---------- */
export function Loading({ label }) {
  const t = useT()
  return (
    <div className="flex items-center gap-3 p-8 text-muted" role="status" aria-live="polite">
      <Spinner /> <span>{label || t('common.loading')}</span>
    </div>
  )
}

export function ErrorState({ error, onRetry }) {
  const t = useT()
  const offline = error && !error.response
  const msg = offline ? t('errors.network') : error?.response?.status === 404 ? t('errors.notFound')
    : error?.response?.status === 403 ? t('errors.forbidden') : error?.response?.data?.error?.message || t('errors.generic')
  return (
    <div className="rounded-xl border border-danger/30 bg-danger-50 p-5 text-danger-700" role="alert">
      <div className="flex items-start gap-3">
        <Icon name="alert" className="mt-0.5 h-5 w-5 shrink-0" />
        <div className="flex-1">
          <p className="font-semibold">{msg}</p>
          {onRetry && <Button variant="secondary" size="sm" className="mt-3" onClick={onRetry}>{t('common.retry')}</Button>}
        </div>
      </div>
    </div>
  )
}

export function EmptyState({ icon = 'inbox', title, children, action }) {
  return (
    <div className="flex flex-col items-center px-6 py-12 text-center">
      <div className="mb-3 rounded-full bg-teal-50 p-3 text-teal"><Icon name={icon} className="h-6 w-6" /></div>
      <p className="font-semibold text-navy">{title}</p>
      {children && <p className="mt-1 max-w-md text-sm text-muted">{children}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}

export function Alert({ tone = 'info', title, children, icon }) {
  const map = { info: 'border-teal-100 bg-teal-50 text-deep', warn: 'border-warn/30 bg-warn-50 text-warn-700',
    danger: 'border-danger/30 bg-danger-50 text-danger-700', success: 'border-success/30 bg-success-50 text-success-700',
    bronze: 'border-bronze/30 bg-bronze-50 text-[#6b5636]' }
  const ic = icon || { info: 'shield', warn: 'alert', danger: 'alert', success: 'check', bronze: 'shield' }[tone]
  return (
    <div className={`flex gap-3 rounded-xl border p-4 text-sm ${map[tone]}`} role={tone === 'danger' ? 'alert' : 'note'}>
      <Icon name={ic} className="mt-0.5 h-5 w-5 shrink-0" />
      <div>{title && <p className="font-semibold">{title}</p>}<div className={title ? 'mt-0.5' : ''}>{children}</div></div>
    </div>
  )
}

/* ---------- Form fields ---------- */
export function Field({ label, hint, error, required, children, id }) {
  const auto = useId()
  const fid = id || auto
  const child = typeof children === 'function' ? children({ id: fid, 'aria-invalid': error ? true : undefined, 'aria-describedby': error ? `${fid}-err` : hint ? `${fid}-hint` : undefined }) : children
  return (
    <div className="space-y-1.5">
      {label && (
        <label htmlFor={fid} className="block text-sm font-semibold text-ink">
          {label} {required && <span className="text-danger" aria-hidden="true">*</span>}
        </label>
      )}
      {child}
      {hint && !error && <p id={`${fid}-hint`} className="text-xs text-muted">{hint}</p>}
      {error && <p id={`${fid}-err`} className="flex items-center gap-1 text-sm text-danger-700"><Icon name="alert" className="h-4 w-4" />{error}</p>}
    </div>
  )
}

const inputCls = 'block w-full rounded-lg border border-line bg-white px-3 py-2.5 text-ink placeholder:text-muted/70 focus:border-teal focus:outline-none focus:ring-2 focus:ring-teal/30 aria-[invalid=true]:border-danger min-h-[44px]'

export function Input(props) { return <input className={inputCls} {...props} /> }
export function Textarea(props) { return <textarea className={`${inputCls} min-h-[96px]`} {...props} /> }
export function Select({ children, ...props }) { return <select className={`${inputCls} pr-8`} {...props}>{children}</select> }

export function Checkbox({ label, hint, ...props }) {
  const id = useId()
  return (
    <div className="flex items-start gap-3">
      <input id={id} type="checkbox" className="mt-1 h-5 w-5 shrink-0 rounded border-line text-teal focus:ring-teal" {...props} />
      <label htmlFor={id} className="text-sm text-ink">{label}{hint && <span className="block text-xs text-muted">{hint}</span>}</label>
    </div>
  )
}

/* ---------- Modal ---------- */
export function Modal({ open, title, onClose, children, footer, wide }) {
  const ref = useRef(null)
  const t = useT()
  useEffect(() => {
    if (!open) return undefined
    const prev = document.activeElement
    ref.current?.querySelector('input,select,textarea,button')?.focus()
    const onKey = (e) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', onKey)
    return () => { document.removeEventListener('keydown', onKey); prev?.focus?.() }
  }, [open, onClose])
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-navy/40 p-0 sm:items-center sm:p-4" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div ref={ref} role="dialog" aria-modal="true" aria-label={title}
        className={`max-h-[92vh] w-full overflow-y-auto rounded-t-2xl bg-white shadow-xl sm:rounded-2xl ${wide ? 'sm:max-w-2xl' : 'sm:max-w-lg'}`}>
        <div className="flex items-center justify-between border-b border-line px-5 py-4">
          <h2 className="text-lg font-semibold text-navy">{title}</h2>
          <button onClick={onClose} className="rounded-lg p-2 text-muted hover:bg-ivory" aria-label={t('common.close')}><Icon name="x" /></button>
        </div>
        <div className="space-y-4 px-5 py-5">{children}</div>
        {footer && <div className="flex flex-wrap justify-end gap-2 border-t border-line px-5 py-4">{footer}</div>}
      </div>
    </div>
  )
}

/* ---------- Tabs ---------- */
export function Tabs({ tabs, value, onChange }) {
  return (
    <div className="-mx-1 mb-5 overflow-x-auto" role="tablist">
      <div className="flex min-w-max gap-1 border-b border-line px-1">
        {tabs.map((tab) => (
          <button key={tab.id} role="tab" aria-selected={value === tab.id} onClick={() => onChange(tab.id)}
            className={`min-h-[44px] border-b-2 px-3 text-sm font-semibold transition-colors ${value === tab.id ? 'border-teal text-navy' : 'border-transparent text-muted hover:text-ink'}`}>
            {tab.label}{tab.count != null && <span className="ml-1.5 rounded-full bg-ivory px-1.5 text-xs text-muted">{tab.count}</span>}
          </button>
        ))}
      </div>
    </div>
  )
}

/* ---------- Definition list ---------- */
export function Detail({ label, children }) {
  return (
    <div>
      <dt className="text-xs font-semibold uppercase tracking-wide text-muted">{label}</dt>
      <dd className="mt-0.5 text-ink">{children ?? '—'}</dd>
    </div>
  )
}

export function Table({ head, children, empty }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-line bg-ivory/60 text-xs uppercase tracking-wide text-muted">
          <tr>{head.map((h) => <th key={h} scope="col" className="whitespace-nowrap px-4 py-3 font-semibold">{h}</th>)}</tr>
        </thead>
        <tbody className="divide-y divide-line">{children}</tbody>
      </table>
      {empty}
    </div>
  )
}
