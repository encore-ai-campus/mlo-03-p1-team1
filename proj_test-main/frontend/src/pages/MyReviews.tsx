import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowUpRight, Star, Trash2 } from 'lucide-react'
import { useApi } from '../hooks'
import { useSession } from '../context'
import { api } from '../api/client'
import { dateLabel } from '../components/ContentCard'
import { Dialog } from '../components/Dialog'
import { EmptyState, ErrorState, Loading, LoginGate } from '../components/States'
import type { UserReview } from '../types'

export function MyReviews() {
  const s = useSession()
  const result = useApi<UserReview[]>(s.user ? '/users/me/reviews' : null)
  const [selected, setSelected] = useState<UserReview | null>(null)
  const [busy, setBusy] = useState(false)
  const remove = async () => {
    if (!selected || busy) return
    setBusy(true)
    try { await api(`/contents/${selected.content_id}/reviews/me`, { method: 'DELETE' }); setSelected(null); s.refresh(); s.toast('리뷰를 삭제했어요.') }
    catch (e) { s.toast((e as Error).message) } finally { setBusy(false) }
  }
  return <div className="container page-content"><Link to="/mypage" className="back-link">마이페이지</Link><div className="page-heading"><h1>내가 쓴 리뷰</h1><p>관람 후 남긴 감상을 확인하고 수정할 수 있습니다.</p></div>
    {!s.ready ? <Loading /> : !s.user ? <LoginGate title="나의 감상 기록을 모아보세요" /> : result.loading ? <Loading /> : result.error ? <ErrorState error={result.error} retry={result.retry} /> : result.data?.length ? <div className="own-review-list">{result.data.map(r => <article key={r.id}><div className="own-review-heading"><Link to={`/contents/${r.content_id}#reviews`}><h2>{r.content_title}<ArrowUpRight size={17} /></h2></Link><time>{dateLabel(r.updated_at.slice(0,10))}</time></div><span className="review-stars" aria-label={`5점 만점에 ${r.rating}점`}>{Array.from({length:5},(_,i)=><Star key={i} size={16} fill={i<r.rating?'currentColor':'none'} />)}</span><p>{r.body}</p><div className="own-review-actions"><Link to={`/contents/${r.content_id}#reviews`} className="text-link">리뷰 수정</Link><button className="text-link" onClick={() => setSelected(r)}><Trash2 size={14} />삭제</button></div></article>)}</div> : <><EmptyState title="아직 작성한 리뷰가 없어요" text="콘텐츠 상세 화면에서 평점과 감상을 남겨보세요." /><Link to="/explore" className="button outline">문화 둘러보기</Link></>}
    <Dialog open={!!selected} close={() => { if (!busy) setSelected(null) }} title="리뷰 삭제"><h2>리뷰를 삭제할까요?</h2><p className="muted">{selected?.content_title}에 남긴 감상과 평점이 삭제됩니다.</p><div className="confirm-actions"><button className="button outline" disabled={busy} onClick={() => setSelected(null)}>취소</button><button className="button primary" disabled={busy} onClick={remove}>{busy?'삭제 중…':'리뷰 삭제'}</button></div></Dialog>
  </div>
}
