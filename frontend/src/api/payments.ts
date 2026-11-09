import { api } from './client'
import type { Order } from '../types'

export function checkout(contentId: number, quantity: number, key: string) {
  return api<Order>('/payments/simulations', {
    method: 'POST', headers: { 'Idempotency-Key': key }, body: JSON.stringify({ content_id: contentId, quantity }),
  })
}
