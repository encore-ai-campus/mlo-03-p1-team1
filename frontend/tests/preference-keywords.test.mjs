import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'
import ts from 'typescript'

const source = await readFile(new URL('../src/preferenceKeywords.ts', import.meta.url), 'utf8')
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext },
})
const { KEYWORD_SECTIONS, MAX_PREFERENCE_TAGS, getKeywordGroups, togglePreferenceTag } =
  await import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`)
const allKeywords = KEYWORD_SECTIONS.flatMap(section => section.groups.flatMap(group => group.keywords))

test('expanded keywords preserve every existing saved keyword and fit the survey API', () => {
  const existing = ['현대미술', '사진', '디자인', '몰입형', '클래식', '재즈', '인디', '이야기', '가족', '야외']
  for (const keyword of existing) assert.ok(allKeywords.includes(keyword))
  assert.ok(allKeywords.length > 90)
  assert.equal(new Set(allKeywords).size, allKeywords.length)
  assert.ok(allKeywords.every(keyword => keyword.trim() === keyword && keyword.length > 0 && keyword.length <= 30))
  assert.equal(MAX_PREFERENCE_TAGS, 10)
})

test('genre suggestions follow selected categories; mood and style remain available to everyone', () => {
  assert.deepEqual(getKeywordGroups('genre', ['음악']).map(group => group.category), ['음악'])
  assert.deepEqual(getKeywordGroups('genre', ['전시', '연극']).map(group => group.category), ['전시', '연극'])
  assert.deepEqual(getKeywordGroups('genre', []), [])
  for (const section of ['mood', 'style']) {
    assert.deepEqual(getKeywordGroups(section, ['음악']), getKeywordGroups(section, ['전시']))
    assert.ok(getKeywordGroups(section, []).length > 0)
  }
  assert.deepEqual(getKeywordGroups('genre', ['전시', '뮤지컬', '연극', '음악', '무용', '축제']).map(group => group.category), ['전시', '뮤지컬', '연극', '음악', '무용', '축제'])
})

test('selection stops at the API limit and allows replacing a selected keyword', () => {
  let tags = []
  for (const keyword of allKeywords) tags = togglePreferenceTag(tags, keyword)
  assert.equal(tags.length, 10)
  const original = [...tags]
  assert.deepEqual(togglePreferenceTag(tags, '새로운 시도'), original)
  const removed = togglePreferenceTag(tags, tags[0])
  assert.equal(removed.length, 9)
  const replaced = togglePreferenceTag(removed, '새로운 시도')
  assert.equal(replaced.length, 10)
  assert.ok(replaced.includes('새로운 시도'))
  assert.deepEqual(tags, original)
})

test('previously saved or hidden keywords survive category changes and remain removable', () => {
  const saved = ['재즈', '예전에 저장한 취향']
  getKeywordGroups('genre', ['전시'])
  const updated = togglePreferenceTag(saved, '사진')
  assert.deepEqual(updated, ['재즈', '예전에 저장한 취향', '사진'])
  assert.deepEqual(togglePreferenceTag(updated, '예전에 저장한 취향'), ['재즈', '사진'])
})
