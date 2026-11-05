import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { ArrowUpRight, Bookmark, Clock3, LogOut, Settings2, Ticket, UserRound } from 'lucide-react'
import { api } from '../api/client'
import { useSession } from '../context'
import { useApi } from '../hooks'
import type { Order, PaymentConfig, Reservation, User } from '../types'
import { dateLabel } from '../components/ContentCard'
import { Dialog } from '../components/Dialog'
import { EmptyState, ErrorState, Loading, LoginGate } from '../components/States'

const STATUS: Record<string, string> = { PENDING: '결제 확인 필요', PAID: '결제 완료', CANCELLED: '취소 완료', PARTIAL_CANCELLED: '부분 취소 · 확인 필요', CONFIRMED: '예약 확정', REVIEW_REQUIRED: '확인 필요' }
export function MyPage() {
  const s = useSession()
  const [params, setParams] = useSearchParams()
  const tab = params.get('tab') || 'reservations'
  const orders = useApi<Order[]>(s.user ? '/payments' : null)
  const reservations = useApi<Reservation[]>(s.user ? '/reservations' : null)
  const config = useApi<PaymentConfig>('/payments/config')
  const [busy, setBusy] = useState(false)
  const [edit, setEdit] = useState(false)
  const [cancel, setCancel] = useState<Order | null>(null)
  const [error, setError] = useState('')
  if (!s.ready) return <div className="container page-content"><Loading /></div>
  if (!s.user) return <div className="container page-content"><LoginGate title="나의 문화생활을 한눈에" /></div>
  const perform = async (path: string, body?: object) => {
    setBusy(true); setError('')
    try { await api(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined }); s.refresh(); setCancel(null); s.toast('처리 결과를 업데이트했어요.') } catch (e) { setError((e as Error).message); s.toast((e as Error).message) } finally { setBusy(false) }
  }
  return <div className="container page-content"><div className="page-heading"><UserRound size={36} className="page-symbol" /><h1>나의 문화생활</h1><p>쌓여가는 취향, 기다려지는 순간들을 모았어요.</p></div><div className="profile-panel"><span className="avatar large">{s.user.name.slice(0, 1)}</span><div><h2>{s.user.name} 님</h2><p>{s.user.email}</p></div><div className="profile-buttons"><button className="button outline" onClick={() => setEdit(true)}>프로필 수정</button><button className="icon-button" aria-label="로그아웃" disabled={busy} onClick={async () => { setBusy(true); try { await s.logout() } catch (e) { s.toast((e as Error).message) } finally { setBusy(false) } }}><LogOut size={19} /></button></div></div>
    <div className="member-preferences"><div><h2>나의 관심사</h2><p>{s.user.categories.length ? s.user.categories.join(' · ') : '아직 관심 분야를 고르지 않았어요.'}</p><p className="muted">선호 지역: {s.user.preferences?.regions.length ? s.user.preferences.regions.join(', ') : '전국'}<br />예산: {s.user.preferences?.max_price == null ? '제한 없음' : s.user.preferences.max_price === 0 ? '무료' : `${s.user.preferences.max_price.toLocaleString()}원 이하`}{s.user.preferences?.companions.length ? ` / ${s.user.preferences.companions.join(', ')}와 함께` : ''}</p></div><button className="button outline" onClick={s.openSurvey}>관심사 수정</button></div>
    <div className="mypage-shortcuts"><Link to="/bookmarks"><Bookmark /><span>찜한 문화</span><ArrowUpRight size={18} /></Link><Link to="/my-reviews"><Settings2 /><span>내가 쓴 리뷰</span><ArrowUpRight size={18} /></Link><Link to="/visits"><Ticket /><span>관람한 문화</span><ArrowUpRight size={18} /></Link><Link to="/history"><Clock3 /><span>최근 본 문화</span><ArrowUpRight size={18} /></Link></div><div className="content-tabs"><button className={tab === 'reservations' ? 'active' : ''} onClick={() => setParams({ tab: 'reservations' })}><Ticket size={17} />예약·이용 내역</button><button className={tab === 'payments' ? 'active' : ''} onClick={() => setParams({ tab: 'payments' })}>주문·결제 내역</button></div>
    {tab === 'payments' ? orders.loading ? <Loading /> : orders.error ? <ErrorState error={orders.error} retry={orders.retry} /> : orders.data?.length ? <div className="order-list">{orders.data.map(o => <article key={o.payment_id}><div><span className={`status-tag ${o.status === 'PAID' ? 'good' : ''}`}>{STATUS[o.status] || o.status}</span><Link to={`/contents/${o.content_id}`}><h3>{o.order_name}</h3></Link><p>{o.quantity}매 · {o.amount.toLocaleString()}원 · {dateLabel(o.created_at.slice(0, 10))}</p><p className="fine-print">주문번호 {o.payment_id}</p></div><div className="order-actions">{o.status === 'PENDING' && <button className="button outline" disabled={busy} onClick={() => perform(`/payments/${o.payment_id}/verify`)}>결제 상태 확인</button>}{o.status === 'PAID' && config.data?.refunds_enabled && <button className="button outline" disabled={busy} onClick={() => { setCancel(o); setError('') }}>전액 취소 요청</button>}</div></article>)}</div> : <EmptyState title="아직 결제 내역이 없어요" text="서비스 내에서 결제한 주문을 이곳에서 확인할 수 있어요." /> : reservations.loading ? <Loading /> : reservations.error ? <ErrorState error={reservations.error} retry={reservations.retry} /> : reservations.data?.length ? <div className="order-list">{reservations.data.map(r => <article key={r.id}><div><span className={`status-tag ${r.status === 'CONFIRMED' ? 'good' : ''}`}>{STATUS[r.status] || r.status}</span><Link to={`/contents/${r.content_id}`}><h3>{r.title}</h3></Link><p>{r.venue} · {dateLabel(r.start_date)}</p></div><strong>{r.quantity}매 · {r.amount.toLocaleString()}원</strong></article>)}</div> : <EmptyState title="아직 예약한 문화가 없어요" text="결제가 확인된 예약을 이곳에 모아드려요." />}
    <Dialog open={edit} close={() => setEdit(false)} title="프로필 수정"><h2>프로필 수정</h2><form className="stack" onSubmit={async e => { e.preventDefault(); const name = new FormData(e.currentTarget).get('name'); setBusy(true); try { s.updateUser(await api<User>('/users/me', { method: 'PATCH', body: JSON.stringify({ name }) })); setEdit(false); s.toast('프로필을 수정했어요.') } catch (e) { s.toast((e as Error).message) } finally { setBusy(false) } }}><label>이름<input name="name" defaultValue={s.user.name} minLength={2} maxLength={40} required /></label><button className="button primary" disabled={busy}>저장하기</button></form></Dialog>
    <Dialog open={!!cancel} close={() => setCancel(null)} title="전액 취소 요청"><h2>예약을 취소할까요?</h2><p>{cancel?.order_name}</p><p className="muted">행사 시작일 전 전액 취소만 지원합니다. 취소 결과는 결제사 확인 후 반영됩니다.</p><form className="stack" onSubmit={e => { e.preventDefault(); const reason = new FormData(e.currentTarget).get('reason'); if (cancel) void perform(`/payments/${cancel.payment_id}/cancel`, { reason }) }}><label>취소 사유<input name="reason" minLength={2} maxLength={200} required placeholder="취소 사유를 입력해 주세요" /></label>{error && <p role="alert" className="form-error">{error}</p>}<button className="button primary" disabled={busy}>{busy ? '취소 확인 중…' : '전액 취소 요청'}</button></form></Dialog>
  </div>
}
