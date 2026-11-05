import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'
import vm from 'node:vm'
import ts from 'typescript'

const source = await readFile(new URL('../src/motion.ts', import.meta.url), 'utf8')
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS },
})

function harness(initial) {
  let now = 0
  let nextId = 0
  const frames = new Map()
  const exports = {}
  let values = [...initial]
  vm.runInNewContext(outputText, {
    exports,
    performance: { now: () => now },
    requestAnimationFrame(callback) { frames.set(++nextId, callback); return nextId },
    cancelAnimationFrame(id) { frames.delete(id) },
  })
  const spring = exports.createSpring(initial, next => { values = [...next] })
  return {
    spring,
    get values() { return values },
    step(count = 1) {
      for (let i = 0; i < count; i++) {
        now += 16
        const callbacks = [...frames.values()]
        frames.clear()
        callbacks.forEach(callback => callback(now))
      }
    },
  }
}

test('a critically damped hover settles without bounce or an endless frame loop', () => {
  const h = harness([0, 1])
  h.spring.to([-5, 1.008])
  for (let i = 0; i < 120; i++) {
    h.step()
    assert.ok(h.values[0] >= -5 && h.values[0] <= 0)
    assert.ok(h.values[1] >= 1 && h.values[1] <= 1.008)
  }
  assert.deepEqual(h.values, [-5, 1.008])
  assert.equal(h.spring.running, false)
})

test('pressing and releasing mid-hover preserves the current presentation value', () => {
  const h = harness([0, 1])
  h.spring.to([-1.5, 1.025])
  h.step(8)
  const beforePress = [...h.values]
  assert.ok(beforePress[0] < 0)
  h.spring.to([0, .96])
  assert.deepEqual(h.values, beforePress)
  h.step(12)
  assert.ok(h.values[1] < beforePress[1])
  const beforeRelease = [...h.values]
  h.spring.to([0, 1])
  assert.deepEqual(h.values, beforeRelease)
  h.step(120)
  assert.deepEqual(h.values, [0, 1])
})

test('reduced motion can snap an active transition and cancel all frames', () => {
  const h = harness([12, .65])
  h.spring.to([0, 1])
  h.step(5)
  h.spring.jump([0, 1])
  assert.deepEqual(h.values, [0, 1])
  assert.equal(h.spring.running, false)
  h.step(20)
  assert.deepEqual(h.values, [0, 1])
})
