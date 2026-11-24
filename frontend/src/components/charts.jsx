import { useState } from 'react'
import { useT } from '../i18n'

/**
 * Single-series horizontal bar chart (magnitude → one hue). Suppressed cells are shown as a
 * hatched stub labelled "fewer than K", never as a number. Hover/focus shows the exact value;
 * a "view as table" toggle provides a non-visual alternative.
 */
export function BarList({ rows, minCell = 5, valueSuffix = '', caption }) {
  const t = useT()
  const [asTable, setAsTable] = useState(false)
  const [hover, setHover] = useState(null)
  const visible = rows.filter((r) => r.value !== 0 || r.suppressed)
  const max = Math.max(1, ...visible.map((r) => r.value || 0))
  const fmt = (r) => (r.suppressed ? t('analytics.suppressed', { k: minCell }) : `${r.value}${valueSuffix}`)

  return (
    <figure>
      <div className="mb-2 flex justify-end">
        <button className="text-xs font-semibold text-teal underline-offset-2 hover:underline" onClick={() => setAsTable((v) => !v)}>
          {asTable ? t('analytics.viewChart') : t('analytics.viewTable')}
        </button>
      </div>
      {visible.length === 0 ? (
        <p className="py-6 text-center text-sm text-muted">{t('analytics.noData')}</p>
      ) : asTable ? (
        <table className="w-full text-sm">
          <tbody className="divide-y divide-line">
            {visible.map((r) => (
              <tr key={r.key}><td className="py-2 pr-4">{r.label}</td><td className="py-2 text-right font-semibold tabular-nums">{fmt(r)}</td></tr>
            ))}
          </tbody>
        </table>
      ) : (
        <ul className="space-y-2.5">
          {visible.map((r) => {
            const pct = r.suppressed ? 0 : (r.value / max) * 100
            return (
              <li key={r.key} className="grid grid-cols-[minmax(7rem,38%)_1fr] items-center gap-3 sm:grid-cols-[12rem_1fr]"
                onMouseEnter={() => setHover(r.key)} onMouseLeave={() => setHover(null)}>
                <span className="truncate text-sm text-ink" title={r.label}>{r.label}</span>
                <div className="relative flex items-center gap-2" tabIndex={0} onFocus={() => setHover(r.key)} onBlur={() => setHover(null)}
                  aria-label={`${r.label}: ${fmt(r)}`}>
                  <div className="h-3.5 flex-1 rounded-r bg-ivory">
                    {r.suppressed ? (
                      <div className="h-full w-6 rounded-r border border-dashed border-muted/60"
                        style={{ backgroundImage: 'repeating-linear-gradient(45deg, #C9D0CC 0 2px, transparent 2px 6px)' }} />
                    ) : (
                      <div className={`h-full rounded-r transition-colors ${hover === r.key ? 'bg-deep' : 'bg-teal'}`} style={{ width: `${Math.max(pct, r.value ? 2 : 0)}%` }} />
                    )}
                  </div>
                  <span className={`w-20 shrink-0 text-right text-sm tabular-nums ${r.suppressed ? 'text-muted' : 'font-semibold text-ink'}`}>{fmt(r)}</span>
                </div>
              </li>
            )
          })}
        </ul>
      )}
      {caption && <figcaption className="mt-3 text-xs text-muted">{caption}</figcaption>}
    </figure>
  )
}

/** Monthly column chart, single series, with per-column hover value. */
export function Columns({ rows, minCell = 5 }) {
  const t = useT()
  const [hover, setHover] = useState(null)
  if (!rows?.length) return <p className="py-6 text-center text-sm text-muted">{t('analytics.noData')}</p>
  const max = Math.max(1, ...rows.map((r) => r.value || 0))
  return (
    <div>
      <div className="flex h-40 items-end gap-1.5 border-b border-line" role="list">
        {rows.map((r) => (
          <div key={r.month} role="listitem" className="relative flex h-full flex-1 flex-col justify-end"
            onMouseEnter={() => setHover(r.month)} onMouseLeave={() => setHover(null)} tabIndex={0}
            onFocus={() => setHover(r.month)} onBlur={() => setHover(null)}
            aria-label={`${r.month}: ${r.suppressed ? t('analytics.suppressed', { k: minCell }) : r.value}`}>
            {hover === r.month && (
              <div className="absolute -top-8 left-1/2 z-10 -translate-x-1/2 whitespace-nowrap rounded bg-navy px-2 py-1 text-xs text-white">
                {r.month}: {r.suppressed ? t('analytics.suppressed', { k: minCell }) : r.value}
              </div>
            )}
            {r.suppressed
              ? <div className="h-2 rounded-t border border-dashed border-muted/60" />
              : <div className={`rounded-t ${hover === r.month ? 'bg-deep' : 'bg-teal'}`} style={{ height: `${(r.value / max) * 100}%` }} />}
          </div>
        ))}
      </div>
      <div className="mt-1 flex gap-1.5 text-[10px] text-muted">
        {rows.map((r, i) => <span key={r.month} className="flex-1 text-center">{i % 2 === 0 || rows.length < 7 ? r.month.slice(2) : ''}</span>)}
      </div>
    </div>
  )
}

export function StatTile({ label, cell, suffix = '', hint, minCell = 5 }) {
  const t = useT()
  const suppressed = cell?.suppressed
  return (
    <div className="rounded-xl border border-line bg-white p-4 shadow-card">
      <p className="text-sm text-muted">{label}</p>
      <p className="mt-1 font-serif text-3xl font-semibold text-navy tabular-nums">
        {suppressed ? <span className="text-lg text-muted">{t('analytics.suppressed', { k: minCell })}</span> : cell?.value == null ? '—' : `${cell.value}${suffix}`}
      </p>
      {hint && <p className="mt-1 text-xs text-muted">{hint}</p>}
    </div>
  )
}
