import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api/client'

/** GET a resource with loading / error state. `path` null = skip. */
export function useApi(path, { params, deps = [] } = {}) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(Boolean(path))
  const mounted = useRef(true)
  const key = path + JSON.stringify(params || {})

  const load = useCallback(async () => {
    if (!path) return
    setLoading(true)
    setError(null)
    try {
      const r = await api.get(path, { params })
      if (mounted.current) setData(r.data)
    } catch (e) {
      if (mounted.current) setError(e)
    } finally {
      if (mounted.current) setLoading(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, ...deps])

  useEffect(() => {
    mounted.current = true
    load()
    return () => { mounted.current = false }
  }, [load])

  // Avoid a one-render gap where a newly enabled path has neither data nor loading state.
  const pending = Boolean(path) && data === null && error === null
  return { data, error, loading: loading || pending, reload: load, setData }
}

/** Wrap a mutation with busy / error state. */
export function useAction(fn) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const run = useCallback(async (...args) => {
    setBusy(true)
    setError(null)
    try {
      return await fn(...args)
    } catch (e) {
      setError(e)
      throw e
    } finally {
      setBusy(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fn])
  return { run, busy, error, setError }
}
