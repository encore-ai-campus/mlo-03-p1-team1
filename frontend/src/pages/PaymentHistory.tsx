import { Link } from 'react-router-dom'
import { useApi } from '../hooks'
import type { Order, Reservation } from '../types'
import { dateLabel } from '../components/ContentCard'
import { EmptyState, ErrorState, Loading } from '../components/States'
import { mergePaymentHistory } from '../paymentHistory'
import '../styles/payment-history.css'

const STATUS: Record<string, string> = { PENDING: '결제 대기', PAID: '결제 완료', CANCELLED: '취소 완료', PARTIAL_CANCELLED: '부분 취소', REVIEW_REQUIRED: '확인 필요' }

export function PaymentHistory() {
  const orders = useApi<Order[]>('/payments')
  const reservations = useApi<Reservation[]>('/reservations')
  const entries = mergePaymentHistory(orders.data || [], reservations.data || [])
  const loading = orders.loading || reservations.loading
  const error = orders.error || reservations.error
  const retry = () => { orders.retry(); reservations.retry() }

  return <section aria-labelledby="payments-title">
    <div className="account-section-heading"><div><h2 id="payments-title">결제 내역</h2><p>결제한 콘텐츠와 이용 일정을 한곳에서 확인하세요.</p></div>{!loading && !error && <span className="payment-history-count">총 {entries.length}건</span>}</div>
    {loading ? <Loading /> : error ? <ErrorState error={error} retry={retry} /> : entries.length ? <div className="order-list payment-history-list" aria-label="결제 내역 목록">{entries.map(entry => <article key={entry.paymentId}>
      <div className="payment-record-details">
        <div className="payment-record-meta"><span className={`status-tag ${entry.status === 'PAID' ? 'good' : ''}`}>{STATUS[entry.status] || entry.status}</span>{entry.createdAt && <time dateTime={entry.createdAt}>{dateLabel(entry.createdAt.slice(0, 10))}</time>}</div>
        <Link to={`/contents/${entry.contentId}`}><h3 className="payment-record-title">{entry.title}</h3></Link>
        {(entry.venue || entry.startDate) && <p className="payment-record-schedule">{entry.venue && <span>{entry.venue}</span>}{entry.startDate && <span>일정 {dateLabel(entry.startDate)}</span>}</p>}
        <p className="fine-print payment-record-id">주문번호 {entry.paymentId}</p>
      </div>
      <div className="payment-record-amount"><strong>{entry.amount.toLocaleString()}원</strong><span>{entry.quantity}매</span>{entry.cancelledAmount > 0 && <span>취소 {entry.cancelledAmount.toLocaleString()}원</span>}</div>
    </article>)}</div> : <EmptyState title="아직 결제 내역이 없어요" text="마음에 드는 콘텐츠를 결제하면 이곳에서 확인할 수 있어요." />}
  </section>
}
