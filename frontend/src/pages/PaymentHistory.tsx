import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { useSession } from '../context'
import { useApi } from '../hooks'
import type { Order, PaymentConfig, Reservation } from '../types'
import { dateLabel } from '../components/ContentCard'
import { Dialog } from '../components/Dialog'
import { EmptyState, ErrorState, Loading } from '../components/States'

const STATUS: Record<string, string> = { PENDING: '결제 확인 필요', PAID: '결제 완료', CANCELLED: '취소 완료', PARTIAL_CANCELLED: '부분 취소 · 확인 필요', CONFIRMED: '예약 확정', REVIEW_REQUIRED: '확인 필요' }

export function PaymentHistory() {
  const s = useSession()
  const orders = useApi<Order[]>('/payments')
  const reservations = useApi<Reservation[]>('/reservations')
  const config = useApi<PaymentConfig>('/payments/config')
  const [busy, setBusy] = useState(false)
  const [cancel, setCancel] = useState<Order | null>(null)
  const [error, setError] = useState('')
  const perform = async (path: string, body?: object) => {
    setBusy(true); setError('')
    try {
      await api(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined })
      s.refresh(); setCancel(null); s.toast('처리 결과를 업데이트했어요.')
    } catch (e) { setError((e as Error).message); s.toast((e as Error).message) } finally { setBusy(false) }
  }

  return <section aria-labelledby="activity-title">
    <div className="account-section-heading"><div><h2 id="activity-title">이용·결제 내역</h2><p>예약 상태와 결제한 주문을 확인하세요.</p></div></div>
    <section className="account-activity-section" aria-labelledby="reservations-title"><h3 id="reservations-title">예약·이용 내역</h3>
      {reservations.loading ? <Loading /> : reservations.error ? <ErrorState error={reservations.error} retry={reservations.retry} /> : reservations.data?.length ? <div className="order-list">{reservations.data.map(r => <article key={r.id}>
        <div><span className={`status-tag ${r.status === 'CONFIRMED' ? 'good' : ''}`}>{STATUS[r.status] || r.status}</span><Link to={`/contents/${r.content_id}`}><h4>{r.title}</h4></Link><p>{r.venue} · {dateLabel(r.start_date)}</p></div>
        <strong>{r.quantity}매 · {r.amount.toLocaleString()}원</strong>
      </article>)}</div> : <EmptyState title="아직 예약한 문화가 없어요" text="결제가 확인된 예약을 이곳에 모아드려요." />}
    </section>
    <section className="account-activity-section" aria-labelledby="orders-title"><h3 id="orders-title">주문·결제 내역</h3>
      {orders.loading ? <Loading /> : orders.error ? <ErrorState error={orders.error} retry={orders.retry} /> : orders.data?.length ? <div className="order-list">{orders.data.map(o => <article key={o.payment_id}>
        <div><span className={`status-tag ${o.status === 'PAID' ? 'good' : ''}`}>{STATUS[o.status] || o.status}</span><Link to={`/contents/${o.content_id}`}><h4>{o.order_name}</h4></Link><p>{o.quantity}매 · {o.amount.toLocaleString()}원 · {dateLabel(o.created_at.slice(0, 10))}</p><p className="fine-print">주문번호 {o.payment_id}</p></div>
        <div className="order-actions">{o.status === 'PENDING' && <button className="button outline" disabled={busy} onClick={() => perform(`/payments/${o.payment_id}/verify`)}>결제 상태 확인</button>}{o.status === 'PAID' && config.data?.refunds_enabled && <button className="button outline" disabled={busy} onClick={() => { setCancel(o); setError('') }}>전액 취소 요청</button>}</div>
      </article>)}</div> : <EmptyState title="아직 결제 내역이 없어요" text="서비스 내에서 결제한 주문을 이곳에서 확인할 수 있어요." />}
    </section>
    <Dialog open={!!cancel} close={() => { if (!busy) setCancel(null) }} title="전액 취소 요청">
      <h2>예약을 취소할까요?</h2><p>{cancel?.order_name}</p><p className="muted">행사 시작일 전 전액 취소만 지원합니다. 취소 결과는 결제사 확인 후 반영됩니다.</p>
      <form className="stack" onSubmit={e => { e.preventDefault(); const reason = new FormData(e.currentTarget).get('reason'); if (cancel) void perform(`/payments/${cancel.payment_id}/cancel`, { reason }) }}>
        <label>취소 사유<input name="reason" minLength={2} maxLength={200} required placeholder="취소 사유를 입력해 주세요" disabled={busy} /></label>
        {error && <p role="alert" className="form-error">{error}</p>}<button className="button primary" disabled={busy}>{busy ? '취소 확인 중…' : '전액 취소 요청'}</button>
      </form>
    </Dialog>
  </section>
}
