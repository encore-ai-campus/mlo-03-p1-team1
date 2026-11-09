import { ArrowRight, ArrowUpRight, Frame, Sparkles } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import type { FormEvent } from 'react'
import type { ContentPage } from '../types'
import { useApi } from '../hooks'
import { useRecommendations } from '../hooks/useRecommendations'
import { useSession } from '../context'
import { track } from '../api/client'
import { ContentCard, safeUrl } from '../components/ContentCard'
import { EmptyState, ErrorState, Loading } from '../components/States'
import './home.css'

export function Home() {
  const navigate = useNavigate()
  const s = useSession()
  const listing = useApi<ContentPage>('/contents?size=8&sort=popular')
  const featured = listing.data?.items.filter(content => content.source !== 'sample').slice(0, 2) ?? []
  const recs = useRecommendations(4)
  const search = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const q = new FormData(e.currentTarget).get('q')
    void track('search', undefined, undefined, { query_length: String(q || '').trim().length })
    navigate('/explore?q=' + encodeURIComponent(String(q || '').trim()))
  }
  return <div className="home-page">
    <section className="container home-hero" aria-labelledby="home-title">
      <div className="home-hero-copy">
        <p className="home-intro"><span />일상과 취향 사이, Oddinary</p>
        <h1 id="home-title">평범한 하루를,<br />취향 있는 하루로.</h1>
        <p className="home-description">마음에 남는 전시부터 기다려온 공연까지.<br />나를 조금 더 나답게 만드는 문화를 만나보세요.</p>
        <div className="home-hero-actions"><Link className="button primary" to="/explore">오늘의 문화 발견하기<ArrowUpRight size={18} /></Link><Link className="text-link" to="/recommendations">나를 위한 추천<ArrowRight size={17} /></Link></div>
      </div>
      <div className="home-artwork" aria-label="문화 콘텐츠 큐레이션">
        <span className="home-art-orbit" aria-hidden="true" />
        {featured.length ? featured.map((content, index) => <Link key={content.id} to={`/contents/${content.id}`} className={`home-art-poster ${index === 0 ? 'poster-music' : 'poster-exhibition'}`} aria-label={`${content.title} 상세 보기`}>
          <img src={content.image_url.startsWith('/posters/') ? content.image_url : safeUrl(content.image_url) || '/posters/fallback.svg'} alt={`${content.title} 포스터`} fetchPriority={index === 0 ? 'high' : 'auto'} onError={event => { if (event.currentTarget.getAttribute('src') !== '/posters/fallback.svg') event.currentTarget.src = '/posters/fallback.svg' }} />
          <span className="home-art-caption"><strong>{content.title}</strong><span>{content.venue}</span></span>
        </Link>) : listing.loading ? <Loading /> : listing.error ? <ErrorState error={listing.error} retry={listing.retry} /> : <EmptyState title="소개할 문화를 준비하고 있어요" />}
        <div className="home-art-note"><span className="home-note-icon"><Frame size={20} /></span><div><strong>새로운 감각을 만나는 순간</strong><span>포스터를 눌러 자세히 만나보세요</span></div><Sparkles size={19} /></div>
      </div>
    </section>

    <section className="container home-discovery" aria-label="문화 콘텐츠 검색">
      <form className="home-search" onSubmit={search}><input aria-label="문화 콘텐츠 검색" name="q" maxLength={100} placeholder="어떤 문화가 궁금하세요?" /><button type="submit" aria-label="검색"><ArrowRight size={22} /></button></form>
    </section>

    <section className="container section home-recommendations" aria-labelledby="recommendation-title">
      <div className="section-heading"><div><h2 id="recommendation-title">{s.user ? s.user.name + ' 님의 다음 취향' : s.preferences ? '고른 취향에 꼭 맞는 문화' : '당신의 다음 취향을 발견하세요'}<Sparkles className="heading-icon" size={25} /></h2><p>{s.preferences ? s.preferences.categories.join(' · ') + (s.user?.survey_completed ? ' 취향과 활동을 바탕으로 골랐어요.' : ' 분야에서 마음에 들 만한 문화를 골랐어요.') : '익숙한 취향부터, 아직 몰랐던 새로운 장면까지.'}</p></div><Link to="/recommendations" className="text-link">추천 더 보기<ArrowRight size={17} /></Link></div>
      <div className="home-preference-bar"><span>{s.preferences ? '지금의 취향: ' + s.preferences.categories.join(', ') : '좋아하는 분야를 고르면 추천이 더 가까워져요.'}</span><button type="button" className="text-link" onClick={s.openSurvey}>{s.preferences ? '취향 다시 고르기' : '내 취향 고르기'}<ArrowRight size={16} /></button></div>
      {recs.loading ? <Loading /> : recs.error ? <ErrorState error={recs.error} retry={recs.retry} /> : recs.data?.items.length ? <div className="card-grid">{recs.data.items.map(c => <ContentCard key={String(c.id) + '-' + c.bookmarked} content={c} recommended />)}</div> : <EmptyState title="다음 취향을 준비하고 있어요" text="새로운 문화가 모이면 이곳에서 가장 먼저 소개할게요." />}
    </section>

    <section className="home-popular" aria-labelledby="popular-title"><div className="container section"><div className="section-heading"><div><h2 id="popular-title">지금, 눈여겨볼 문화</h2><p>이번 일상에 더하고 싶은 순간을 골라보세요.</p></div><Link to="/explore" className="text-link">전체 보기<ArrowRight size={17} /></Link></div>
      {listing.loading ? <Loading /> : listing.error ? <ErrorState error={listing.error} retry={listing.retry} /> : listing.data?.items.length ? <><div className="card-grid">{listing.data.items.map(c => <ContentCard key={String(c.id) + '-' + c.bookmarked} content={c} />)}</div></> : <EmptyState />}
    </div></section>

    <section className="container home-taste-section"><div className="home-taste"><div className="home-taste-copy"><span className="home-taste-icon"><Sparkles size={25} /></span><h2>좋아하는 걸 알려주세요.<br />다음 발견은 우리가 도울게요.</h2><p>나의 취향을 담은 작은 선택이<br />더 마음에 드는 추천으로 이어집니다.</p><button type="button" className="button primary" onClick={s.openSurvey}>{s.preferences ? '나의 취향 다시 고르기' : '나의 취향 알아보기'}<ArrowUpRight size={18} /></button></div><div className="home-taste-art" aria-hidden="true"><span className="taste-orbit orbit-one" /><span className="taste-orbit orbit-two" /><span className="taste-center"><Sparkles size={52} strokeWidth={1.2} /></span><span className="taste-float float-one">전시</span><span className="taste-float float-two">재즈</span><span className="taste-float float-three">나의 취향</span></div></div></section>
  </div>
}
