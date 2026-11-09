import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { api, getToken, setToken } from './api/client'
import type { User } from './types'

interface Session {
  user: User | null; ready: boolean; authOpen: boolean; surveyOpen: boolean;
  openAuth: () => void; closeAuth: () => void; openSurvey: () => void; closeSurvey: () => void;
  acceptAuth: (token: string, user: User) => void; updateUser: (user: User) => void;
  logout: () => Promise<void>; toast: (text: string) => void; revision: number; refresh: () => void;
}
const SessionContext = createContext<Session | null>(null)
export const useSession = () => useContext(SessionContext)!

export function SessionProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [ready, setReady] = useState(!getToken())
  const [authOpen, setAuthOpen] = useState(false)
  const [surveyOpen, setSurveyOpen] = useState(false)
  const [message, setMessage] = useState('')
  const [revision, setRevision] = useState(0)
  const refresh = useCallback(() => setRevision(r => r + 1), [])
  const toast = useCallback((text: string) => setMessage(text), [])
  useEffect(() => {
    const expired = () => { setUser(null); refresh(); toast('로그인이 만료되었습니다. 다시 로그인해 주세요.') }
    window.addEventListener('culturepick:expired', expired)
    if (getToken()) api<User>('/users/me').then(setUser).catch(error => toast(error.message)).finally(() => setReady(true))
    return () => window.removeEventListener('culturepick:expired', expired)
  }, [refresh, toast])
  useEffect(() => { if (message) { const timer = setTimeout(() => setMessage(''), 4200); return () => clearTimeout(timer) } }, [message])
  const acceptAuth = (token: string, next: User) => {
    setToken(token); setUser(next); setAuthOpen(false); refresh()
    if (!next.survey_completed) setSurveyOpen(true)
  }
  const logout = async () => {
    await api('/auth/logout', { method: 'POST' })
    setToken(null); setUser(null); refresh(); toast('로그아웃했습니다.')
  }
  return <SessionContext.Provider value={{ user, ready, authOpen, surveyOpen, openAuth: () => setAuthOpen(true), closeAuth: () => setAuthOpen(false),
    openSurvey: () => user ? setSurveyOpen(true) : setAuthOpen(true), closeSurvey: () => setSurveyOpen(false), acceptAuth,
    updateUser: setUser, logout, toast, revision, refresh }}>
    {children}
    {message && <div className="toast" role="status">{message}<button onClick={() => setMessage('')} aria-label="알림 닫기">×</button></div>}
  </SessionContext.Provider>
}
