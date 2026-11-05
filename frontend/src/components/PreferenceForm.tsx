import { useRef, useState } from 'react'
import { ArrowLeft, ArrowRight, AudioLines, Check, Drama, Flower2, Frame, Music2, PartyPopper, Sparkles } from 'lucide-react'
import { useSession } from '../context'
import { CATEGORIES } from '../types'
import { MAX_PREFERENCE_TAGS, togglePreferenceTag } from '../preferenceKeywords'
import { PreferenceKeywords } from './PreferenceKeywords'
import type { TastePreferences } from '../preferences'

const ICONS = [Frame, Drama, AudioLines, Music2, Flower2, PartyPopper]

interface PreferenceFormProps {
  onSaved?: () => void;
  onSubmitPreferences?: (preferences: TastePreferences) => Promise<void>;
  onBack?: () => void;
  submitLabel?: string;
}

export function PreferenceForm({ onSaved, onSubmitPreferences, onBack, submitLabel = '취향 저장하기' }: PreferenceFormProps) {
  const s = useSession()
  const [categories, setCategories] = useState<string[]>(s.preferences?.categories || [])
  const [tags, setTags] = useState<string[]>(s.preferences?.tags || [])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [step, setStep] = useState<0 | 1>(0)
  const heading = useRef<HTMLHeadingElement>(null)
  const move = (next: 0 | 1) => {
    setStep(next)
    requestAnimationFrame(() => heading.current?.focus())
  }
  const toggle = (value: string, list: string[], setter: (values: string[]) => void) => setter(list.includes(value) ? list.filter(v => v !== value) : [...list, value])

  return <form className={`preference-form${step === 1 ? ' preference-form-keywords' : ''}`} onSubmit={async e => {
    e.preventDefault()
    if (!categories.length) return
    if (step === 0) { move(1); return }
    if (tags.length > MAX_PREFERENCE_TAGS) return
    setBusy(true); setError('')
    try {
      await (onSubmitPreferences || s.savePreferences)({ categories, tags })
      onSaved?.()
    } catch (e) { setError((e as Error).message) } finally { setBusy(false) }
  }}>
    <div className="survey-progress" role="progressbar" aria-label="취향 설정 진행" aria-valuemin={1} aria-valuemax={2} aria-valuenow={step + 1}><span className="complete" /><span className={step === 1 ? 'complete' : ''} /></div>
    <div key={step} className="survey-step">
      <p className="survey-step-label" aria-live="polite">{step + 1} / 2 · {step === 0 ? '좋아하는 문화' : '마음이 가는 키워드'}</p>
      <h3 className="survey-step-heading" ref={heading} tabIndex={-1}>{step === 0 ? '어떤 문화에 마음이 끌리나요?' : '조금 더 나다운 취향으로.'}</h3>
      <p className="survey-step-copy">{step === 0 ? '좋아하는 분야를 하나 이상 골라주세요. 여러 개도 좋아요.' : '세부 장르부터 분위기와 관람 스타일까지, 나의 취향을 더 알려주세요.'}</p>
      {step === 0 ? <fieldset disabled={busy}><legend className="sr-only">좋아하는 문화 분야 선택</legend>
        <div className="choice-grid">{CATEGORIES.map((c, i) => { const Icon = ICONS[i]; return <button type="button" key={c} aria-pressed={categories.includes(c)} className={'choice category-choice' + (categories.includes(c) ? ' selected' : '')} onClick={() => toggle(c, categories, setCategories)}><Icon size={27} strokeWidth={1.5} /><span>{c}</span>{categories.includes(c) && <Check className="choice-check" size={15} />}</button> })}</div>
        <p className="survey-selection" aria-live="polite">{categories.length ? categories.length + '개 분야를 골랐어요' : '취향에 맞는 추천의 첫걸음이에요'}</p>
      </fieldset> : <fieldset disabled={busy}><legend className="sr-only">관심 키워드 선택</legend>
        <PreferenceKeywords categories={categories} tags={tags} onToggle={keyword => setTags(current => togglePreferenceTag(current, keyword))} />
        <p className="survey-selection">선택한 문화: {categories.join(', ')}</p>
      </fieldset>}
    </div>
    {error && <p className="form-error" role="alert">{error}</p>}
    <div className="survey-actions">{(step === 1 || onBack) && <button type="button" className="button outline" disabled={busy} onClick={() => step === 1 ? move(0) : onBack?.()}><ArrowLeft size={17} />이전</button>}<button className="button primary" disabled={!categories.length || (step === 1 && tags.length > MAX_PREFERENCE_TAGS) || busy}>{busy ? '저장 중…' : step === 0 ? '다음으로' : submitLabel}{step === 0 ? <ArrowRight size={17} /> : <Sparkles size={17} />}</button></div>
  </form>
}
