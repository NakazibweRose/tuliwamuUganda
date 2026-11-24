import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { api, refreshSession, setAccessToken, setSessionEndedHandler } from '../api/client'
import { useI18n } from '../i18n'

const AuthContext = createContext(null)
const IDLE_MINUTES = { staff: 20, beneficiary: 10 }

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [status, setStatus] = useState('checking') // checking | ready
  const [notice, setNotice] = useState(null)
  const { setLang } = useI18n()
  const idleTimer = useRef(null)

  const clear = useCallback((reason) => {
    setAccessToken(null)
    setUser(null)
    if (reason) setNotice(reason)
  }, [])

  useEffect(() => {
    setSessionEndedHandler(() => clear('sessionExpired'))
    // Restore a session from the httpOnly refresh cookie (no tokens in browser storage).
    refreshSession()
      .then((d) => { setUser(d.user); setLang(d.user.preferred_language) })
      .catch(() => {})
      .finally(() => setStatus('ready'))
  }, [clear, setLang])

  const login = useCallback(async (username, password) => {
    const r = await api.post('/auth/login/', { username, password })
    setAccessToken(r.data.access)
    setUser(r.data.user)
    setNotice(null)
    if (r.data.user.preferred_language) setLang(r.data.user.preferred_language)
    return r.data.user
  }, [setLang])

  const logout = useCallback(async (reason) => {
    try { await api.post('/auth/logout/') } catch { /* offline: cookie expires on its own */ }
    clear(reason)
  }, [clear])

  // Automatic sign-out after inactivity (shared or unsafe devices).
  useEffect(() => {
    if (!user) return undefined
    const minutes = user.permissions?.beneficiary_portal ? IDLE_MINUTES.beneficiary : IDLE_MINUTES.staff
    const reset = () => {
      clearTimeout(idleTimer.current)
      idleTimer.current = setTimeout(() => logout('idleLogout'), minutes * 60 * 1000)
    }
    const events = ['pointerdown', 'keydown', 'scroll']
    events.forEach((e) => window.addEventListener(e, reset, { passive: true }))
    reset()
    return () => { clearTimeout(idleTimer.current); events.forEach((e) => window.removeEventListener(e, reset)) }
  }, [user, logout])

  const refreshMe = useCallback(async () => {
    const r = await api.get('/auth/me/')
    setUser(r.data)
    return r.data
  }, [])

  const value = useMemo(() => ({ user, status, login, logout, notice, setNotice, refreshMe, setUser }), [user, status, login, logout, notice, refreshMe])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export const useAuth = () => useContext(AuthContext)

/** Quick exit: leave immediately to a neutral website and drop the session. */
export function quickExit() {
  try { navigator.sendBeacon?.(((import.meta.env.VITE_API_BASE_URL || '') + '/api/auth/logout/')) } catch { /* ignore */ }
  setAccessToken(null)
  window.location.replace('https://www.google.com/search?q=weather+kampala')
}
