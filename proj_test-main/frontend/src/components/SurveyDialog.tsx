import { useEffect, useState } from 'react'
import { Check, SlidersHorizontal } from 'lucide-react'
import { api } from '../api/client'
import { CATEGORIES, REGIONS } from '../types'
import type { User } from '../types'
import { useSession } from '../context'
import { Dialog } from './Dialog'

const TAGS = ['현대미술', '사진', '디자인', '몰입형', '클래식', '재즈', '인디', '이야기', '가족', '야외']
export function SurveyDialog() {
  const s = useSession()
  const [categories, setCategories] = useState<string[]>([])
  const [tags, setTags] = useState<string[]>([])
  const [regions, setRegions] = useState<string[]>([])
  const [budget, setBudget] = useState('')
  const [companions, setCompanions] = useState<string[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => { if (s.surveyOpen) { setCategories(s.user?.categories || []); setTags(s.user?.tags || []); setRegions(s.user?.preferences?.regions || []); setBudget(s.user?.preferences?.max_price?.toString() ?? ''); setCompanions(s.user?.preferences?.companions || []); setError('') } }, [s.surveyOpen, s.user])
  const toggle = (value: string, list: string[], setter: (v: string[]) => void) => setter(list.includes(value) ? list.filter(v => v !== value) : [...list, value])
  const save = async () => {
    setBusy(true); setError('')
    try {
      s.updateUser(await api<User>('/surveys/me', { method: 'PUT', body: JSON.stringify({ categories, tags, preferences: { regions, max_price: budget === '' ? null : Number(budget), companions } }) }))
      s.closeSurvey(); s.refresh(); s.toast('취향을 저장했어요. 나만의 추천을 확인해 보세요.')
    } catch (e) { setError((e as Error).message) } finally { setBusy(false) }
  }
  return <Dialog open={s.surveyOpen} close={s.closeSurvey} title="취향 설정">
    <div className="dialog-symbol"><SlidersHorizontal /></div><h2>관심 분야를 알려주세요</h2><p className="muted">좋아하는 분야를 하나 이상 골라 주세요.<br />취향은 언제든 다시 바꿀 수 있어요.</p>
    <h3>좋아하는 문화</h3><div className="choice-grid">{CATEGORIES.map(c => <button key={c} aria-pressed={categories.includes(c)} className={categories.includes(c) ? 'choice selected' : 'choice'} onClick={() => toggle(c, categories, setCategories)}>{c}{categories.includes(c) && <Check size={16} />}</button>)}</div>
    <h3>더 끌리는 키워드 <span className="muted small">선택</span></h3><div className="tag-choices">{TAGS.map(t => <button key={t} aria-pressed={tags.includes(t)} className={tags.includes(t) ? 'tag selected' : 'tag'} onClick={() => toggle(t, tags, setTags)}>#{t}</button>)}</div>
    <h3>자주 찾는 지역 <span className="muted small">선택</span></h3><div className="tag-choices">{REGIONS.map(r => <button key={r} aria-pressed={regions.includes(r)} className={regions.includes(r) ? 'tag selected' : 'tag'} onClick={() => toggle(r, regions, setRegions)}>{r}</button>)}</div>
    <label className="survey-budget">한 번의 문화생활 예산<select value={budget} onChange={e => setBudget(e.target.value)}><option value="">제한 없음</option><option value="0">무료</option><option value="20000">2만원 이하</option><option value="50000">5만원 이하</option><option value="100000">10만원 이하</option></select></label>
    <h3>주로 누구와 함께하나요? <span className="muted small">선택</span></h3><div className="tag-choices">{['혼자','친구','연인','가족'].map(v => <button key={v} aria-pressed={companions.includes(v)} className={companions.includes(v) ? 'tag selected' : 'tag'} onClick={() => toggle(v, companions, setCompanions)}>{v}</button>)}</div>
    {error && <p className="form-error" role="alert">{error}</p>}<button className="button primary full" disabled={!categories.length || busy} onClick={save}>{busy ? '저장 중…' : '나의 취향 저장하기'}<Check size={17} /></button>
  </Dialog>
}
