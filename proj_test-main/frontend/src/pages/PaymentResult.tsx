import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../api/client'
import { useSession } from '../context'
import type { Order } from '../types'
import { LoginGate } from '../components/States'

export function PaymentResult() {
  const [params] = useSearchParams()
  const s = useSession()
  const [message, setMessage] = useState('결제 정보를 확인하고 있어요…')
  const [busy, setBusy] = useState(false)
  const [nonce, setNonce] = useState(0)
  const paymentId = params.get('paymentId')
  const code = params.get('code')
  useEffect(() => {
    if (!s.ready || !s.user) return
    if (code) { setMessage('결제가 완료되지 않았습니다. 결제 내역에서 상태를 확인해 주세요.'); return }
    if (!paymentId) { setMessage('결제 식별자가 없습니다. 결제 내역에서 확인해 주세요.'); return }
    let active = true
    setBusy(true)
    api<Order>(`/payments/${encodeURIComponent(paymentId)}/verify`, { method: 'POST' }).then(o => { if (active) setMessage(o.status === 'PAID' ? '결제가 확인되어 예약을 완료했어요.' : '아직 결제가 확인되지 않았어요. 잠시 후 다시 확인해 주세요.') }).catch(e => { if (active) setMessage(e.message) }).finally(() => { if (active) setBusy(false) })
    return () => { active = false }
  }, [paymentId, code, s.ready, s.user, nonce])
  if (s.ready && !s.user) return <div className="container page-content"><LoginGate title="로그인 후 결제 결과를 확인해 주세요" /></div>
  return <div className="container page-content"><div className="empty-state"><h1>결제 결과 확인</h1><p role="status">{message}</p>{paymentId && !code && <button className="button outline" disabled={busy} onClick={() => setNonce(n => n + 1)}>다시 확인</button>}<Link to="/mypage?tab=payments" className="button primary">결제 내역으로 이동</Link></div></div>
}
