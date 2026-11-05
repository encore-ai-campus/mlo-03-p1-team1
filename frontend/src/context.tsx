import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { api, getToken, setToken } from './api/client'
import type { User } from './types'
import { dismissOnboarding, onboardingDismissed, readPreferences, storePreferences } from './preferences'
import type { TastePreferences } from './preferences'
import { useLocation } from 'react-router-dom'

interface Session {
  user: User | null; ready: boolean; authOpen: boolean; surveyOpen: boolean;
  openAuth: () => void; closeAuth: () => void; closeSurvey: () => void;
  openSurvey: () => void; preferences: TastePreferences | null; savePreferences: (preferences: TastePreferences) => Promise<void>;
  acceptAuth: (token: string, user: User, mode: 'register' | 'login') => void; updateUser: (user: User) => void;
  logout: () => Promise<void>; toast: (text: string) => void; revision: number; refresh: () => void;
}
const SessionContext = createContext<Session | null>(null)
export const useSession = () => useContext(SessionContext)!

export function SessionProvider({ children }: { children: ReactNode }) {
  const { pathname } = useLocation()
  const [user, setUser] = useState<User | null>(null)
  const [guestPreferences, setGuestPreferences] = useState<TastePreferences | null>(readPreferences)
  const [dismissed, setDismissed] = useState(onboardingDismissed)
  const [ready, setReady] = useState(!getToken())
  const [authOpen, setAuthOpen] = useState(false)
  const [surveyOpen, setSurveyOpen] = useState(false)
  const [message, setMessage] = useState('')
  const [revision, setRevision] = useState(0)
  const refresh = useCallback(() => setRevision(r => r + 1), [])
  const toast = useCallback((text: string) => setMessage(text), [])
  const preferences = user?.survey_completed ? { categories: user.categories, tags: user.tags } : guestPreferences
  useEffect(() => {
    if (ready && pathname === '/' && !preferences?.categories.length && !dismissed && !authOpen) setSurveyOpen(true)
  }, [ready, pathname, preferences?.categories.length, dismissed, authOpen])
  const closeSurvey = () => { dismissOnboarding(); setDismissed(true); setSurveyOpen(false) }
  const savePreferences = async (next: TastePreferences) => {
    if (user) setUser(await api<User>('/surveys/me', { method: 'PUT', body: JSON.stringify(next) }))
    else { storePreferences(next); setGuestPreferences(next) }
    refresh()
    toast('취향을 저장했어요. 선택한 문화로 추천을 준비할게요.')
  }
  useEffect(() => {
    const expired = () => { setUser(null); setSurveyOpen(false); refresh(); toast('로그인이 만료되었습니다. 다시 로그인해 주세요.') }
    window.addEventListener('culturepick:expired', expired)
    if (getToken()) api<User>('/users/me').then(setUser).catch(error => toast(error.message)).finally(() => setReady(true))
    return () => window.removeEventListener('culturepick:expired', expired)
  }, [refresh, toast])
  useEffect(() => { if (message) { const timer = setTimeout(() => setMessage(''), 4200); return () => clearTimeout(timer) } }, [message])
  const acceptAuth = (token: string, next: User, mode: 'register' | 'login') => {
    setToken(token); setUser(next); setAuthOpen(false); refresh()
    setSurveyOpen(mode === 'register' && !next.survey_completed)
  }
  const logout = async () => {
    await api('/auth/logout', { method: 'POST' })
    setToken(null); setUser(null); setSurveyOpen(false); refresh(); toast('로그아웃했습니다.')
  }
  return <SessionContext.Provider value={{ user, ready, authOpen, surveyOpen, preferences, savePreferences,
    openAuth: () => { setSurveyOpen(false); setAuthOpen(true) }, closeAuth: () => setAuthOpen(false),
    closeSurvey, openSurvey: () => { setAuthOpen(false); setSurveyOpen(true) }, acceptAuth,
    updateUser: setUser, logout, toast, revision, refresh }}>
    {children}
    {message && <div className="toast" role="status">{message}<button onClick={() => setMessage('')} aria-label="알림 닫기">×</button></div>}
  </SessionContext.Provider>
}
