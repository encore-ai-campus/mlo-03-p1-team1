import { ArrowRight, ArrowUpRight, Frame, Drama, Music2, AudioLines, Flower2, PartyPopper, Search } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { useState } from 'react'
import type { FormEvent } from 'react'
import { CATEGORIES } from '../types'
import type { ContentPage } from '../types'
import { useApi } from '../hooks'
import { useSession } from '../context'
import { track } from '../api/client'
import { ContentCard } from '../components/ContentCard'
import { EmptyState, ErrorState, Loading } from '../components/States'

export const categoryIcons = [Frame, Drama, AudioLines, Music2, Flower2, PartyPopper]
export function Home() {
  const navigate = useNavigate()
  const s = useSession()
  const [category, setCategory] = useState('')
  const [region, setRegion] = useState('')
  const [sort, setSort] = useState('popular')
  const listing = useApi<ContentPage>(`/contents?size=10&sort=${sort}${category ? `&category=${encodeURIComponent(category)}` : ''}${region ? `&region=${encodeURIComponent(region)}` : ''}`)
  const recs = useApi<ContentPage>('/recommendations?size=4')
  const search = (e: FormEvent<HTMLFormElement>) => { e.preventDefault(); const q = new FormData(e.currentTarget).get('q'); void track('search'); navigate(`/explore?q=${encodeURIComponent(String(q || ''))}`) }
  return <div className="overview-page">
    <section className="hero-section container"><div className="hero">
      <div className="hero-copy"><h1>이번 주말, 어떤 문화를 만날까요?</h1><p>전시부터 공연까지. 일정과 장소를 비교하고 마음에 드는 문화를 모아보세요.</p><Link to="/explore" className="text-link">전체 문화 탐색<ArrowUpRight size={17} /></Link></div>
      <Link to="/explore?category=전시" className="hero-art" aria-label="전시 둘러보기"><img src="/images/gallery.jpg" alt="붉은 벽을 따라 회화와 조각이 전시된 미술관" /><div className="art-label"><h2>작품 앞에 머무는 시간</h2><span className="art-arrow"><ArrowUpRight size={25} /></span></div><span className="photo-credit">Photo · Unsplash</span></Link>
    </div></section>
    <section className="container overview-toolbar"><div className="content-tabs" role="group" aria-label="콘텐츠 분야">{['', ...CATEGORIES].map(c => <button key={c} className={category === c ? 'active' : ''} onClick={() => { setCategory(c); void track('filter_use', undefined, c || undefined) }} aria-pressed={category === c}>{c || '전체'}</button>)}</div><form onSubmit={search} role="search" className="home-search"><input type="search" enterKeyHint="search" aria-label="문화 콘텐츠 검색" name="q" maxLength={100} placeholder="전시·공연·장소 검색" /><button type="submit" aria-label="검색"><Search size={20} /></button></form></section>
    <section className="container section overview-listing"><div className="section-heading"><div><h2>전시와 공연 한눈에{listing.data && <span className="overview-count">{listing.data.total.toLocaleString()}건</span>}</h2></div><div className="overview-options"><label><span className="sr-only">지역</span><select value={region} onChange={e => setRegion(e.target.value)}><option value="">전국</option>{['서울','경기','인천','부산','대구','광주','대전','울산','세종','강원','충북','충남','전북','전남','경북','경남','제주'].map(r => <option key={r}>{r}</option>)}</select></label><label><span className="sr-only">목록 정렬</span><select value={sort} onChange={e => setSort(e.target.value)}><option value="popular">찜 많은 순</option><option value="ending">종료 임박순</option><option value="latest">최근 수집순</option></select></label><Link to="/explore" className="text-link">전체 보기<ArrowUpRight size={17} /></Link></div></div>
      {listing.loading ? <Loading /> : listing.error ? <ErrorState error={listing.error} retry={listing.retry} /> : listing.data?.items.length ? <><div className="card-grid">{listing.data.items.map(c => <ContentCard key={`${c.id}-${c.bookmarked}`} content={c} />)}</div>{listing.data.items.some(c => c.is_sample) && <p className="sample-notice">‘샘플’ 표시는 기능 체험을 위한 가상 행사입니다. 실제 개최·예매 정보가 아닙니다.</p>}</> : <EmptyState />}
    </section>
    <section className="taste-band"><div className="container taste-band-inner"><div><h2>어떤 문화를 좋아하세요?</h2><p>관심 분야를 고르면 취향에 맞는 전시와 공연을 추천합니다.</p></div><button className="button light" onClick={s.openSurvey}>{s.user?.survey_completed ? '관심 분야 수정' : '관심 분야 고르기'}<ArrowUpRight size={18} /></button></div></section>
    <section className="container section"><div className="section-heading"><div><h2>{s.user ? `${s.user.name} 님을 위한 추천` : '취향을 넓혀줄 문화'}</h2><p>{s.user ? '관심 분야와 최근 활동을 바탕으로 골랐어요.' : '새롭게 만나볼 전시와 공연을 모았습니다.'}</p></div><Link to="/recommendations" className="text-link">추천 더 보기<ArrowRight size={17} /></Link></div>
      {recs.loading ? <Loading /> : recs.error ? <ErrorState error={recs.error} retry={recs.retry} /> : recs.data?.items.length ? <div className="card-grid">{recs.data.items.map(c => <ContentCard key={`${c.id}-${c.bookmarked}`} content={c} recommended />)}</div> : <EmptyState title="아직 추천할 콘텐츠가 없어요" text="새 문화정보가 수집되면 이곳에서 만날 수 있어요." />}
    </section>
  </div>
}
