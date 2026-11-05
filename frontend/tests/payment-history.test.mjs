import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'
import ts from 'typescript'

const source = await readFile(new URL('../src/paymentHistory.ts', import.meta.url), 'utf8')
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext },
})
const { mergePaymentHistory } = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`)
const order = {
  payment_id: 'sim-one', content_id: 1, order_name: '전시', quantity: 2, amount: 36000,
  cancelled_amount: 0, currency: 'KRW', status: 'PAID', is_simulated: true, created_at: '2026-11-05T06:00:00Z',
}
const reservation = {
  id: 1, payment_id: 'sim-one', content_id: 1, title: '전시', venue: '전시관', start_date: '2026-12-01',
  status: 'CONFIRMED', quantity: 2, amount: 36000, is_simulated: true,
}

test('a payment and its usage record produce one entry with venue and schedule', () => {
  const entries = mergePaymentHistory([order], [reservation])
  assert.equal(entries.length, 1)
  assert.equal(entries[0].paymentId, order.payment_id)
  assert.equal(entries[0].venue, '전시관')
  assert.equal(entries[0].startDate, '2026-12-01')
  assert.equal(entries[0].status, 'PAID')
  assert.equal(entries[0].amount, 36000)
})

test('duplicate API rows do not duplicate payments or override authoritative order amounts', () => {
  const entries = mergePaymentHistory([order, order], [reservation, { ...reservation, amount: 999 }])
  assert.equal(entries.length, 1)
  assert.equal(entries[0].amount, 36000)
})

test('a pending order remains visible without a usage record', () => {
  const entries = mergePaymentHistory([{ ...order, status: 'PENDING' }], [])
  assert.equal(entries.length, 1)
  assert.equal(entries[0].status, 'PENDING')
  assert.equal(entries[0].venue, null)
})

test('usage outside the order query limit is retained without inventing a payment date', () => {
  const entries = mergePaymentHistory([], [reservation])
  assert.equal(entries.length, 1)
  assert.equal(entries[0].title, '전시')
  assert.equal(entries[0].createdAt, null)
  assert.equal(entries[0].status, 'PAID')
})

test('partial cancellation status and amounts survive the merge', () => {
  const entries = mergePaymentHistory([{ ...order, status: 'PARTIAL_CANCELLED', cancelled_amount: 18000 }], [reservation])
  assert.equal(entries[0].status, 'PARTIAL_CANCELLED')
  assert.equal(entries[0].cancelledAmount, 18000)
})
