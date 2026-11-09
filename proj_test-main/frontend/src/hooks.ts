import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from './api/client'
import { useSession } from './context'

export function useApi<T>(path: string | null) {
  const { revision, ready } = useSession()
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [nonce, setNonce] = useState(0)
  const loadedPath = useRef<string | null>(null)
  const retry = useCallback(() => setNonce(n => n + 1), [])
  useEffect(() => {
    if (!path || !ready) { setLoading(Boolean(path)); if (!path) { loadedPath.current = null; setData(null) } return }
    let active = true
    const abort = new AbortController()
    setLoading(loadedPath.current !== path); setError('')
    api<T>(path, { signal: abort.signal }).then(result => { if (active) { loadedPath.current = path; setData(result) } }).catch(e => { if (active) setError(e.message) }).finally(() => { if (active) setLoading(false) })
    return () => { active = false; abort.abort() }
  }, [path, revision, ready, nonce])
  return { data, error, loading, retry }
}
