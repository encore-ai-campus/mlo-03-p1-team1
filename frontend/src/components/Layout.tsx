import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { Bookmark, Search, ArrowUpRight, UserRound } from 'lucide-react'
import { useSession } from '../context'
import { AuthDialog } from './AuthDialog'
import { SurveyDialog } from './SurveyDialog'
import { Brand } from './Brand'
import { PageTransition } from './PageTransition'
import { useAppleInteractions } from '../hooks/useAppleInteractions'

export function Layout() {
  const s = useSession()
  const navigate = useNavigate()
  useAppleInteractions()
  return <>
    <a className="skip-link" href="#main">본문 바로가기</a>
    <header className="header"><div className="container header-inner">
      <Brand />
      <nav aria-label="주 메뉴"><NavLink to="/" end>발견하기</NavLink><NavLink to="/explore">문화 탐색</NavLink><NavLink to="/recommendations">취향 추천<span className="nav-spark">✳</span></NavLink></nav>
      <div className="header-actions"><button className="icon-button" aria-label="문화 콘텐츠 검색" onClick={() => navigate('/explore?focus=search')}><Search size={21} /></button><Link className="icon-button" to="/mypage/bookmarks" aria-label="찜한 콘텐츠"><Bookmark size={20} /></Link>
        {s.user ? <Link className="profile-link" to="/mypage"><span className="avatar">{s.user.name.slice(0, 1)}</span><span>{s.user.name} 님</span></Link> : <button className="login-button" onClick={s.openAuth}>로그인 <UserRound size={15} /></button>}
      </div>
    </div></header>
    <main id="main"><PageTransition><Outlet /></PageTransition></main>
    <footer className="footer"><div className="container"><div className="footer-top"><div><Brand footer /><p>평범한 일상에, 특별한 취향.<br />나의 다음 문화를 만나는 곳, Oddinary.</p></div><div className="footer-links"><Link to="/explore">문화 탐색<ArrowUpRight size={15} /></Link><Link to="/recommendations">취향 추천<ArrowUpRight size={15} /></Link><Link to="/mypage">마이페이지<ArrowUpRight size={15} /></Link></div></div><div className="footer-bottom"><span>© {new Date().getFullYear()} Oddinary</span><span>문화정보의 일정과 가격은 주최 기관에서 최종 확인해 주세요.</span></div></div></footer>
    <AuthDialog /><SurveyDialog />
  </>
}
