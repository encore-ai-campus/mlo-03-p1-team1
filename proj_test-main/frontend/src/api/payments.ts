import { requestPayment } from '@portone/browser-sdk/v2'
import { api } from './client'
import type { Order, PaymentConfig, User } from '../types'

export async function checkout(contentId: number, quantity: number, user: User, key: string) {
  const config = await api<PaymentConfig>('/payments/config')
  if (!config.enabled) throw new Error('결제 준비 중입니다. 현재는 콘텐츠 탐색과 찜을 이용해 주세요.')
  const order = await api<Order>('/payments/orders', {
    method: 'POST', headers: { 'Idempotency-Key': key }, body: JSON.stringify({ content_id: contentId, quantity }),
  })
  const response = await requestPayment({
    storeId: import.meta.env.VITE_PORTONE_STORE_ID || config.store_id,
    channelKey: import.meta.env.VITE_PORTONE_CHANNEL_KEY || config.channel_key,
    paymentId: order.payment_id, orderName: order.order_name, totalAmount: order.amount,
    currency: 'CURRENCY_KRW', payMethod: 'CARD',
    customer: { customerId: String(user.id), fullName: user.name, email: user.email },
    customData: { order_id: order.payment_id }, redirectUrl: `${location.origin}/payment/result`,
  })
  if (response?.code) throw new Error(response.message || '결제가 완료되지 않았습니다. 결제 내역에서 상태를 확인해 주세요.')
  return api<Order>(`/payments/${encodeURIComponent(order.payment_id)}/verify`, { method: 'POST' })
}
