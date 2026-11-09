import { activityContext } from './activity'
import type { ActivityDetails, ClientEventType } from './activity'

export const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1').replace(/\/$/, '')
const TOKEN_KEY = 'culturepick.session'
export const getToken = () => sessionStorage.getItem(TOKEN_KEY)
export const setToken = (token: string | null) => token ? sessionStorage.setItem(TOKEN_KEY, token) : sessionStorage.removeItem(TOKEN_KEY)

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message) }
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  if (options.body) headers.set('Content-Type', 'application/json')
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  try {
    const context = activityContext()
    headers.set('X-Activity-Anonymous-Id', context.anonymous_id)
    headers.set('X-Activity-Session-Id', context.session_id)
    if (context.page_path) headers.set('X-Activity-Page', context.page_path)
  } catch { /* Storage restrictions must not prevent normal API requests. */ }
  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, { ...options, headers, signal: options.signal ?? AbortSignal.timeout(20000) })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    throw new ApiError(0, '서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.')
  }
  const body = await response.json().catch(() => ({}))
  if (!response.ok) {
    if (response.status === 401 && token) {
      setToken(null)
      window.dispatchEvent(new Event('culturepick:expired'))
    }
    const message = typeof body.detail === 'string' ? body.detail : '입력한 값과 형식을 확인해 주세요.'
    throw new ApiError(response.status, message)
  }
  return body as T
}

export async function track(event_type: ClientEventType, content_id?: number, category?: string, details: ActivityDetails = {}) {
  try {
    const token = getToken()
    const body = JSON.stringify({ event_id: crypto.randomUUID(), event_type, content_id, category, ...activityContext(), ...details })
    // Keep one event_id on retry and never attribute an old event to a new login.
    for (let attempt = 0; attempt < 2; attempt++) {
      if (getToken() !== token) return
      try { await api('/history/events', { method: 'POST', body, keepalive: true }); return }
      catch (error) {
        if (attempt || (error instanceof ApiError && error.status > 0 && error.status < 500)) return
        await new Promise(resolve => setTimeout(resolve, 500))
      }
    }
  } catch { /* Analytics failure must not block browsing. */ }
}
