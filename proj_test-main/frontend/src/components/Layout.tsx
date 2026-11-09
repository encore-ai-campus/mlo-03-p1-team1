import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { Bookmark, Search, ArrowUpRight, UserRound, Compass, SlidersHorizontal } from 'lucide-react'
import { useSession } from '../context'
import { AuthDialog } from './AuthDialog'
import { SurveyDialog } from './SurveyDialog'

export function Layout() {
  const s = useSession()
  const navigate = useNavigate()
  return <>
    <a className="skip-link" href="#main">본문 바로가기</a>
    <header className="header"><div className="container header-inner">
      <Link to="/" className="brand" aria-label="Oddinary 홈">Oddinary<span className="brand-descriptor">오디너리</span></Link>
      <nav className="desktop-navigation" aria-label="주 메뉴"><NavLink to="/" end>발견하기</NavLink><NavLink to="/explore">문화 탐색</NavLink><NavLink to="/map">지도</NavLink><NavLink to="/recommendations">취향 추천</NavLink></nav>
      <div className="header-actions"><button className="icon-button" aria-label="문화 콘텐츠 검색" onClick={() => navigate('/explore?focus=search')}><Search size={21} /></button><Link className="icon-button" to="/bookmarks" aria-label="찜한 콘텐츠"><Bookmark size={20} /></Link>
        {s.user ? <Link className="profile-link" to="/mypage"><span className="avatar">{s.user.name.slice(0, 1)}</span><span>{s.user.name} 님</span></Link> : <button className="login-button" onClick={s.openAuth}>로그인 <UserRound size={15} /></button>}
      </div>
    </div></header>
    <main id="main"><Outlet /></main>
    <nav className="mobile-navigation" aria-label="주 메뉴">
      <NavLink to="/" end><Compass size={21} aria-hidden="true" /><span>발견</span></NavLink>
      <NavLink to="/explore"><Search size={21} aria-hidden="true" /><span>탐색</span></NavLink>
      <NavLink to="/recommendations"><SlidersHorizontal size={21} aria-hidden="true" /><span>취향 추천</span></NavLink>
      <NavLink to="/bookmarks"><Bookmark size={21} aria-hidden="true" /><span>찜한 문화</span></NavLink>
    </nav>
    <footer className="footer"><div className="container"><div className="footer-top"><div><Link to="/" className="brand">Oddinary.</Link><p>문화가 일상이 되는 순간.<br />나의 취향이 닿는 곳, 오디너리.</p></div><div className="footer-links"><Link to="/explore">문화 탐색<ArrowUpRight size={15} /></Link><Link to="/recommendations">취향 추천<ArrowUpRight size={15} /></Link><Link to="/map">지도 탐색<ArrowUpRight size={15} /></Link><Link to="/mypage">마이페이지<ArrowUpRight size={15} /></Link>{s.user?.is_admin && <Link to="/admin">운영 현황<ArrowUpRight size={15} /></Link>}</div></div><div className="footer-bottom"><span>© {new Date().getFullYear()} Oddinary</span><span>문화정보의 일정과 가격은 주최 기관에서 최종 확인해 주세요.</span></div></div></footer>
    <AuthDialog /><SurveyDialog />
  </>
}
