import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'
import ts from 'typescript'

const source = await readFile(new URL('../src/preferences.ts', import.meta.url), 'utf8')
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext },
})
const { readPreferences, storePreferences, onboardingDismissed, dismissOnboarding } =
  await import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`)

function withStorage(t, storage) {
  const original = Object.getOwnPropertyDescriptor(globalThis, 'localStorage')
  Object.defineProperty(globalThis, 'localStorage', { value: storage, configurable: true })
  t.after(() => {
    if (original) Object.defineProperty(globalThis, 'localStorage', original)
    else delete globalThis.localStorage
  })
}

function memoryStorage() {
  const data = new Map()
  return {
    getItem: key => data.get(key) ?? null,
    setItem: (key, value) => data.set(key, value),
  }
}

test('a new browser has no saved preferences or dismissed onboarding', t => {
  withStorage(t, memoryStorage())
  assert.equal(readPreferences(), null)
  assert.equal(onboardingDismissed(), false)
})

test('preferences and onboarding dismissal persist independently', t => {
  withStorage(t, memoryStorage())
  const preferences = { categories: ['음악', '전시'], tags: ['재즈'] }
  storePreferences(preferences)
  assert.deepEqual(readPreferences(), preferences)
  assert.equal(onboardingDismissed(), false)
  dismissOnboarding()
  assert.equal(onboardingDismissed(), true)
  assert.deepEqual(readPreferences(), preferences)
  storePreferences({ categories: ['연극'], tags: [] })
  assert.deepEqual(readPreferences(), { categories: ['연극'], tags: [] })
  assert.equal(onboardingDismissed(), true)
})

test('corrupt or incompatible stored data falls back safely', t => {
  const storage = memoryStorage()
  withStorage(t, storage)
  for (const value of ['{', 'null', '[]', '{}', '{"categories":"음악","tags":[]}', '{"categories":["음악"],"tags":[3]}']) {
    storage.setItem('culturepick.preferences', value)
    assert.equal(readPreferences(), null)
  }
  storage.setItem('culturepick.onboarding.dismissed', 'false')
  assert.equal(onboardingDismissed(), false)
})

test('blocked storage and write quota errors do not crash the app', t => {
  withStorage(t, {
    getItem() { throw new Error('SecurityError') },
    setItem() { throw new Error('QuotaExceededError') },
  })
  assert.equal(readPreferences(), null)
  assert.equal(onboardingDismissed(), false)
  assert.doesNotThrow(() => storePreferences({ categories: ['음악'], tags: [] }))
  assert.doesNotThrow(dismissOnboarding)
})
