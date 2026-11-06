import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowUpRight } from 'lucide-react'
import { useSession } from '../context'
import { useApi } from '../hooks'
import { checkout } from '../api/payments'
import { track } from '../api/client'
import type { Content, PaymentConfig } from '../types'
import { safeUrl } from './ContentCard'
import { Dialog } from './Dialog'

export function SimulationCheckout({ content }: { content: Content }) {
  const s = useSession()
  const navigate = useNavigate()
  const config = useApi<PaymentConfig>(content.price > 0 ? '/payments/config' : null)
  const [quantity, setQuantity] = useState(1)
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const requestKey = useRef(crypto.randomUUID())
  const inFlight = useRef(false)
  useEffect(() => {
    requestKey.current = crypto.randomUUID()
    setQuantity(1); setOpen(false); setError('')
  }, [content.id])

  if (content.price <= 0) return <>
    <p className="detail-notice">{content.price_text === '무료' ? '무료 콘텐츠는 결제가 필요하지 않아요.' : '관람료가 확인된 콘텐츠에서 결제할 수 있어요.'}</p>
    {safeUrl(content.source_url) && <a className="button outline full" href={safeUrl(content.source_url)} target="_blank" rel="noreferrer">공식 홈페이지에서 확인<ArrowUpRight size={18} /></a>}
  </>

  const ready = config.data?.enabled && config.data.mode === 'simulation'
  const total = content.price * quantity
  const close = () => { if (!inFlight.current) setOpen(false) }
  const pay = async () => {
    if (!s.user) { setOpen(false); s.openAuth(); return }
    if (inFlight.current) return
    inFlight.current = true
    setBusy(true); setError('')
    try {
      const order = await checkout(content.id, quantity, requestKey.current)
      if (order.status !== 'PAID' || !order.is_simulated) throw new Error('결제 상태를 확인하지 못했어요. 결제 내역에서 확인해 주세요.')
      setOpen(false); s.refresh(); s.toast('결제가 완료됐어요.')
      navigate('/mypage/payments')
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : '결제를 완료하지 못했어요.')
    } finally { inFlight.current = false; setBusy(false) }
  }

  return <>
    <div className="booking-box">
      <label>매수<select value={quantity} disabled={busy} onChange={event => { setQuantity(Number(event.target.value)); requestKey.current = crypto.randomUUID() }}>{[1, 2, 3, 4].map(value => <option key={value} value={value}>{value}매</option>)}</select></label>
      <strong>{total.toLocaleString()}원</strong>
      <button className="button primary" disabled={!s.ready || busy || (!!s.user && !ready)} onClick={() => {
        if (!s.user) { s.openAuth(); return }
        setError(''); setOpen(true); void track('payment_checkout_open', content.id)
      }}>{!s.user ? '로그인 후 결제' : ready ? '결제하기' : '결제 준비 중'}</button>
    </div>
    {config.error && <p className="form-error" role="alert">{config.error} <button className="text-link" onClick={config.retry}>다시 확인</button></p>}
    <Dialog open={open} close={close} title="결제 확인">
      <h2>결제 정보를 확인해 주세요</h2>
      <p className="muted">선택한 콘텐츠와 결제 금액을 확인해 주세요.</p>
      <dl className="profile-details">
        <div><dt>콘텐츠</dt><dd>{content.title}</dd></div>
        <div><dt>매수</dt><dd>{quantity}매</dd></div>
        <div><dt>결제 금액</dt><dd>{total.toLocaleString()}원</dd></div>
      </dl>
      <p className="fine-print">실제 금액이 청구되지 않는 체험용 결제입니다.</p>
      {error && <p className="form-error" role="alert">{error}</p>}
      <div className="profile-form-actions"><button type="button" className="button outline" disabled={busy} onClick={close}>취소</button><button type="button" className="button primary" disabled={busy} onClick={pay}>{busy ? '결제 처리 중…' : '결제하기'}</button></div>
    </Dialog>
  </>
}
