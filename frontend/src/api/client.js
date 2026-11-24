import axios from 'axios'

// The access token lives only in memory (never localStorage). The refresh token is an httpOnly
// cookie the browser sends to /api/auth/refresh/ — JavaScript can never read it.
let accessToken = null
let onSessionEnded = () => {}
let refreshing = null

export const setAccessToken = (t) => { accessToken = t }
export const getAccessToken = () => accessToken
export const setSessionEndedHandler = (fn) => { onSessionEnded = fn }

const baseURL = (import.meta.env.VITE_API_BASE_URL || '') + '/api'

export const api = axios.create({ baseURL, withCredentials: true, timeout: 20000 })

api.interceptors.request.use((config) => {
  if (accessToken) config.headers.Authorization = `Bearer ${accessToken}`
  return config
})

export async function refreshSession() {
  if (!refreshing) {
    refreshing = axios
      .post(`${baseURL}/auth/refresh/`, null, { withCredentials: true, timeout: 20000 })
      .then((r) => { setAccessToken(r.data.access); return r.data })
      .finally(() => { refreshing = null })
  }
  return refreshing
}

api.interceptors.response.use(
  (r) => r,
  async (error) => {
    const original = error.config
    const status = error.response?.status
    const isAuthCall = original?.url?.startsWith('/auth/')
    if (status === 401 && !original._retried && !isAuthCall) {
      original._retried = true
      try {
        await refreshSession()
        return api(original)
      } catch {
        setAccessToken(null)
        onSessionEnded()
      }
    }
    // Retry idempotent GETs once on network failure (unstable connections).
    if (!error.response && original && original.method === 'get' && !original._netRetried) {
      original._netRetried = true
      await new Promise((res) => setTimeout(res, 1500))
      return api(original)
    }
    return Promise.reject(error)
  },
)

/** Turn an axios error into {message, fields} for display. */
export function describeError(error, t) {
  if (!error) return null
  if (!error.response) return { message: t ? t('errors.network') : 'Network problem. Check your connection and try again.', fields: {} }
  const e = error.response.data?.error
  const fields = {}
  if (e?.details && typeof e.details === 'object') {
    for (const [k, v] of Object.entries(e.details)) fields[k] = Array.isArray(v) ? v.join(' ') : String(v)
  }
  let message = e?.message || (t ? t('errors.generic') : 'Something went wrong.')
  if (fields.detail) message = fields.detail
  else if (fields.duplicate_warning) message = fields.duplicate_warning
  if (error.response.status === 404) message = t ? t('errors.notFound') : 'Not found, or you do not have access.'
  return { message, fields, status: error.response.status }
}
