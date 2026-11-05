import type { Order, Reservation } from './types'

export interface PaymentHistoryEntry {
  paymentId: string
  contentId: number
  title: string
  quantity: number
  amount: number
  cancelledAmount: number
  status: string
  createdAt: string | null
  venue: string | null
  startDate: string | null
}

export function mergePaymentHistory(orders: Order[], reservations: Reservation[]): PaymentHistoryEntry[] {
  const usage = new Map(reservations.map(item => [item.payment_id, item]))
  const entries = new Map<string, PaymentHistoryEntry>()
  for (const order of orders) {
    const reservation = usage.get(order.payment_id)
    entries.set(order.payment_id, {
      paymentId: order.payment_id, contentId: order.content_id, title: order.order_name,
      quantity: order.quantity, amount: order.amount, cancelledAmount: order.cancelled_amount,
      status: order.status, createdAt: order.created_at,
      venue: reservation?.venue || null, startDate: reservation?.start_date || null,
    })
  }
  // Retain older usage records even if their order is outside the orders API limit.
  for (const reservation of reservations) {
    if (entries.has(reservation.payment_id)) continue
    entries.set(reservation.payment_id, {
      paymentId: reservation.payment_id, contentId: reservation.content_id, title: reservation.title,
      quantity: reservation.quantity, amount: reservation.amount, cancelledAmount: 0,
      status: reservation.status === 'CONFIRMED' ? 'PAID' : reservation.status,
      createdAt: null, venue: reservation.venue || null, startDate: reservation.start_date,
    })
  }
  return [...entries.values()]
}
