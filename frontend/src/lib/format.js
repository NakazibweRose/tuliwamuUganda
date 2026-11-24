export function fmtDate(value, lang = 'en', opts = {}) {
  if (!value) return '—'
  const d = new Date(value)
  const locale = lang === 'sw' ? 'sw-TZ' : 'en-GB'
  try {
    return d.toLocaleDateString(locale, { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'Africa/Kampala', ...opts })
  } catch {
    return d.toDateString()
  }
}

export function fmtDateTime(value, lang = 'en') {
  if (!value) return '—'
  return fmtDate(value, lang, { hour: '2-digit', minute: '2-digit' })
}

export function relativeDays(value) {
  if (!value) return null
  const ms = new Date(value).getTime() - Date.now()
  return Math.round(ms / 86400000)
}

/** Convert a value from <input type="datetime-local"> (Kampala time) to ISO. */
export function localInputToIso(v) {
  return v ? new Date(v).toISOString() : null
}
export function isoToLocalInput(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}
