import { Bookmark, MapPin } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useState } from 'react'
import { api, track } from '../api/client'
import { useSession } from '../context'
import type { Content } from '../types'

export const priceLabel = (c: Content) => c.price_text || (c.price ? `${c.price.toLocaleString('ko-KR')}원` : '가격 확인 필요')
export const dateLabel = (date: string) => date.replaceAll('-', '.')
export const safeUrl = (url: string) => /^https?:\/\//i.test(url) ? url : undefined
export function ContentCard({ content, recommended = false, onChange }: { content: Content; recommended?: boolean; onChange?: () => void }) {
  const s = useSession()
  const [busy, setBusy] = useState(false)
  const [marked, setMarked] = useState(content.bookmarked)
  const [failed, setFailed] = useState(false)
  const bookmark = async () => {
    if (!s.user) { s.openAuth(); return }
    if (busy) return
    setBusy(true)
    try {
      await api(`/bookmarks/${content.id}`, { method: marked ? 'DELETE' : 'PUT' })
      setMarked(!marked); s.toast(marked ? '찜을 해제했어요.' : '찜한 콘텐츠에 담았어요.'); s.refresh(); onChange?.()
    } catch (e) { s.toast((e as Error).message) } finally { setBusy(false) }
  }
  return <article className="content-card">
    <div className="poster-wrap"><Link to={`/contents/${content.id}`} className="poster-link" aria-label={`${content.title} 상세 보기`} onClick={() => { if (recommended) void track('recommendation_click', content.id) }}>
      <img src={failed || !content.image_url ? '/posters/fallback.svg' : (content.image_url.startsWith('/posters/') ? content.image_url : safeUrl(content.image_url) || '/posters/fallback.svg')} onError={() => setFailed(true)} alt={`${content.title} 포스터`} loading="lazy" />
      {content.is_sample && <span className="sample-badge">샘플</span>}
    </Link><button className={`bookmark-button ${marked ? 'marked' : ''}`} aria-label={`${content.title} ${marked ? '찜 해제' : '찜하기'}`} aria-pressed={marked} disabled={busy} onClick={bookmark}><Bookmark size={20} fill={marked ? 'currentColor' : 'none'} /></button></div>
    <div className="card-meta"><span className="category-text">{content.category}</span><span>{content.region}</span>{content.rating && <span className="card-rating">★ {content.rating.toFixed(1)}</span>}</div>
    <Link to={`/contents/${content.id}`} className="card-title">{content.title}</Link>
    <p className="card-venue"><MapPin size={13} />{content.venue}</p><p className="card-date">{dateLabel(content.start_date)} – {dateLabel(content.end_date)}</p>
    <div className="card-bottom"><span>{priceLabel(content)}</span>{content.tags.slice(0, 1).map(t => <span className="card-tag" key={t}>#{t}</span>)}</div>
    {recommended && content.recommendation_reason && <p className="recommendation-reason">{content.recommendation_reason}</p>}
  </article>
}
