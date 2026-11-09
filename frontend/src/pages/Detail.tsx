import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, Bookmark, CalendarDays, MapPin, Share2, Star, Ticket } from 'lucide-react'
import { api, track } from '../api/client'
import { SimulationCheckout } from '../components/SimulationCheckout'
import { useApi } from '../hooks'
import { useSession } from '../context'
import type { Content, Review } from '../types'
import { dateLabel, priceLabel, safeUrl } from '../components/ContentCard'
import { EmptyState, ErrorState, Loading } from '../components/States'

export function Detail() {
  const { id } = useParams()
  const result = useApi<Content>(`/contents/${id}`)
  const reviews = useApi<Review[]>(`/contents/${id}/reviews`)
  const s = useSession()
  const view = useRef('')
  const [rating, setRating] = useState(5)
  const [body, setBody] = useState('')
  const [busy, setBusy] = useState(false)
  const [failed, setFailed] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => { if (result.data && s.user && view.current !== `${id}-${s.user.id}`) { view.current = `${id}-${s.user.id}`; void track('content_view', result.data.id) } }, [result.data, id, s.user])
  useEffect(() => { setFailed(false); setError('') }, [id])
  useEffect(() => { const own = reviews.data?.find(r => r.user_id === s.user?.id); setBody(own?.body || ''); setRating(own?.rating || 5) }, [reviews.data, s.user?.id])
  if (result.loading) return <div className="container page-content"><Loading /></div>
  if (result.error) return <div className="container page-content"><ErrorState error={result.error} retry={result.retry} /></div>
  const c = result.data!
  const bookmark = async () => {
    if (!s.user) return s.openAuth()
    if (busy) return
    setBusy(true)
    try { await api(`/bookmarks/${c.id}`, { method: c.bookmarked ? 'DELETE' : 'PUT' }); s.refresh(); s.toast(c.bookmarked ? '찜을 해제했어요.' : '찜한 콘텐츠에 담았어요.') } catch (e) { s.toast((e as Error).message) } finally { setBusy(false) }
  }
  const saveReview = async () => {
    if (!s.user) return s.openAuth()
    setBusy(true); setError('')
    try { await api(`/contents/${id}/reviews/me`, { method: 'PUT', body: JSON.stringify({ rating, body }) }); s.refresh(); s.toast('리뷰를 저장했어요.') } catch (e) { setError((e as Error).message) } finally { setBusy(false) }
  }
  return <div className="container page-content detail-page"><Link to="/explore" className="back-link"><ArrowLeft size={16} />문화 탐색</Link><div className="detail-top"><div className="detail-poster"><img src={failed ? '/posters/fallback.svg' : c.image_url.startsWith('/posters/') ? c.image_url : safeUrl(c.image_url) || '/posters/fallback.svg'} alt={`${c.title} 포스터`} onError={() => setFailed(true)} /></div><div className="detail-summary"><div className="detail-badges"><span>{c.category}</span><span>{c.region}</span>{c.is_sample && <span className="sample-label">샘플 콘텐츠</span>}</div><h1>{c.title}</h1><p className="detail-subtitle">{c.subtitle}</p><div className="detail-facts"><div><CalendarDays size={19} /><span>기간</span><strong>{dateLabel(c.start_date)} – {dateLabel(c.end_date)}</strong></div><div><MapPin size={19} /><span>장소</span><strong>{c.venue}</strong></div><div><Ticket size={19} /><span>관람료</span><strong>{priceLabel(c)}</strong></div><div><Star size={19} /><span>평점</span><strong>{c.rating ? `${c.rating.toFixed(1)} / 5 (${c.review_count}개 리뷰)` : '첫 번째 리뷰를 남겨보세요'}</strong></div></div><div className="detail-tags">{c.tags.map(t => <span key={t}>#{t}</span>)}</div><div className="detail-actions"><button className={`button outline ${c.bookmarked ? 'is-marked' : ''}`} aria-pressed={c.bookmarked} disabled={busy} onClick={bookmark}><Bookmark size={18} fill={c.bookmarked ? 'currentColor' : 'none'} />{c.bookmarked ? '찜한 콘텐츠' : '찜하기'}</button><button className="button outline" onClick={async () => { try { await navigator.clipboard.writeText(location.href); s.toast('링크를 복사했어요.') } catch { s.toast('주소창의 링크를 복사해 주세요.') } }}><Share2 size={17} />공유</button></div>
      <SimulationCheckout content={c} />
    </div></div><div className="detail-body"><section><h2>이 문화를 소개해요</h2><p className="description">{c.description}</p><h3>찾아가는 곳</h3><p className="muted">{c.venue}<br />{c.address || '상세 주소는 주최 기관에서 확인해 주세요.'}</p><p className="fine-print">{c.is_sample ? 'Oddinary에서 제작한 샘플 정보입니다.' : `정보 출처: ${c.source}. 수집일 ${dateLabel(c.collected_at.slice(0, 10))}.`}<br />일정·운영시간·가격은 주최 기관의 최종 안내를 확인해 주세요.</p></section><section className="reviews-section"><h2>함께 나누는 감상 <span>{reviews.data?.length || 0}</span></h2><p className="muted">어떤 순간이 가장 기억에 남았나요?</p>{s.user ? <form className="review-form" onSubmit={e => { e.preventDefault(); void saveReview() }}><fieldset className="rating-input"><legend>나의 평점</legend>{[1, 2, 3, 4, 5].map(n => <label key={n}><input type="radio" name="rating" value={n} checked={rating === n} onChange={() => setRating(n)} aria-label={`${n}점`} /><Star size={25} fill={n <= rating ? 'currentColor' : 'none'} /></label>)}</fieldset><label className="sr-only" htmlFor="review-body">감상 리뷰</label><textarea id="review-body" value={body} onChange={e => setBody(e.target.value)} minLength={5} maxLength={2000} required placeholder="나의 감상을 5자 이상 남겨주세요." /><div className="review-form-footer"><span>{body.length}/2000</span><button className="button primary" disabled={busy}>{busy ? '저장 중…' : '리뷰 저장'}</button></div>{error && <p className="form-error" role="alert">{error}</p>}</form> : <div className="review-login"><span>감상을 기록하고 싶다면</span><button className="text-link" onClick={s.openAuth}>로그인하기</button></div>}
      {reviews.loading ? <p role="status">리뷰를 불러오는 중…</p> : reviews.error ? <ErrorState error={reviews.error} retry={reviews.retry} /> : reviews.data?.length ? <div className="review-list">{reviews.data.map(r => <article key={r.id}><div className="review-user"><span className="avatar">{r.name.slice(0, 1)}</span><strong>{r.name}</strong><span className="review-stars">{'★'.repeat(r.rating)}{'☆'.repeat(5 - r.rating)}</span><time>{dateLabel(r.updated_at.slice(0, 10))}</time></div><p>{r.body}</p>{r.user_id === s.user?.id && <button className="text-link small" disabled={busy} onClick={async () => { setBusy(true); try { await api(`/contents/${id}/reviews/me`, { method: 'DELETE' }); s.refresh(); s.toast('리뷰를 삭제했어요.') } catch (e) { s.toast((e as Error).message) } finally { setBusy(false) } }}>리뷰 삭제</button>}</article>)}</div> : <EmptyState title="아직 나눠진 감상이 없어요" text="첫 번째 리뷰로 이야기를 시작해 보세요." />}
    </section></div></div>
}
