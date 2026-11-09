import { useState } from 'react'
import { Navigate, NavLink, Outlet, useSearchParams } from 'react-router-dom'
import { Bookmark, ChevronRight, Clock3, LogOut, Settings2, Ticket, UserRound } from 'lucide-react'
import { useSession } from '../context'
import { Loading, LoginGate } from '../components/States'
import './account.css'

const SECTIONS = [
  { to: '/mypage', label: '나의 정보', Icon: UserRound, end: true },
  { to: '/mypage/bookmarks', label: '찜한 콘텐츠', Icon: Bookmark },
  { to: '/mypage/history', label: '최근 본 콘텐츠', Icon: Clock3 },
  { to: '/mypage/preferences', label: '취향 설정', Icon: Settings2 },
  { to: '/mypage/payments', label: '결제 내역', Icon: Ticket },
]

export function MyPage() {
  const s = useSession()
  const [params] = useSearchParams()
  const [busy, setBusy] = useState(false)
  if (params.get('tab') === 'payments' || params.get('tab') === 'reservations') return <Navigate to="/mypage/payments" replace />
  if (!s.ready) return <div className="container page-content"><Loading /></div>
  if (!s.user) return <div className="container page-content"><LoginGate title="나의 문화생활을 한눈에" /></div>

  return <div className="container page-content account-page">
    <div className="page-heading"><h1>마이페이지</h1><p>나의 정보와 좋아하는 문화를 한곳에서 관리하세요.</p></div>
    <div className="account-layout">
      <aside className="account-sidebar">
        <div className="account-identity"><span className="avatar large">{s.user.name.slice(0, 1)}</span><div><strong>{s.user.name} 님</strong><span>{s.user.email}</span></div></div>
        <nav className="account-nav" aria-label="마이페이지 메뉴">{SECTIONS.map(({ to, label, Icon, end }) => <NavLink key={to} to={to} end={end}><Icon size={19} /><span>{label}</span><ChevronRight size={16} /></NavLink>)}</nav>
        <button className="account-logout" disabled={busy} onClick={async () => {
          setBusy(true)
          try { await s.logout() } catch (e) { s.toast((e as Error).message) } finally { setBusy(false) }
        }}><LogOut size={17} />{busy ? '로그아웃 중…' : '로그아웃'}</button>
      </aside>
      <div className="account-content"><Outlet /></div>
    </div>
  </div>
}
