import { useRef, useState } from 'react'
import { ArrowLeft, ArrowRight, AudioLines, Check, Drama, Flower2, Frame, Music2, PartyPopper, Sparkles } from 'lucide-react'
import { useSession } from '../context'
import { CATEGORIES } from '../types'

const TAGS = ['현대미술', '사진', '디자인', '몰입형', '클래식', '재즈', '인디', '이야기', '가족', '야외']
const ICONS = [Frame, Drama, AudioLines, Music2, Flower2, PartyPopper]

export function PreferenceForm({ onSaved }: { onSaved?: () => void }) {
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

  return <form className="preference-form" onSubmit={async e => {
    e.preventDefault()
    if (!categories.length) return
    if (step === 0) { move(1); return }
    setBusy(true); setError('')
    try {
      await s.savePreferences({ categories, tags })
      onSaved?.()
    } catch (e) { setError((e as Error).message) } finally { setBusy(false) }
  }}>
    <div className="survey-progress" role="progressbar" aria-label="취향 설정 진행" aria-valuemin={1} aria-valuemax={2} aria-valuenow={step + 1}><span className="complete" /><span className={step === 1 ? 'complete' : ''} /></div>
    <div key={step} className="survey-step">
      <p className="survey-step-label" aria-live="polite">{step + 1} / 2 · {step === 0 ? '좋아하는 문화' : '마음이 가는 키워드'}</p>
      <h3 className="survey-step-heading" ref={heading} tabIndex={-1}>{step === 0 ? '어떤 문화에 마음이 끌리나요?' : '조금 더 나다운 취향으로.'}</h3>
      <p className="survey-step-copy">{step === 0 ? '좋아하는 분야를 하나 이상 골라주세요. 여러 개도 좋아요.' : '마음에 드는 키워드를 골라주세요. 선택하지 않아도 괜찮아요.'}</p>
      {step === 0 ? <fieldset disabled={busy}><legend className="sr-only">좋아하는 문화 분야 선택</legend>
        <div className="choice-grid">{CATEGORIES.map((c, i) => { const Icon = ICONS[i]; return <button type="button" key={c} aria-pressed={categories.includes(c)} className={'choice category-choice' + (categories.includes(c) ? ' selected' : '')} onClick={() => toggle(c, categories, setCategories)}><Icon size={27} strokeWidth={1.5} /><span>{c}</span>{categories.includes(c) && <Check className="choice-check" size={15} />}</button> })}</div>
        <p className="survey-selection" aria-live="polite">{categories.length ? categories.length + '개 분야를 골랐어요' : '취향에 맞는 추천의 첫걸음이에요'}</p>
      </fieldset> : <fieldset disabled={busy}><legend className="sr-only">관심 키워드 선택</legend>
        <div className="tag-choices">{TAGS.map(t => <button type="button" key={t} aria-pressed={tags.includes(t)} className={tags.includes(t) ? 'tag selected' : 'tag'} disabled={!tags.includes(t) && tags.length >= 10} onClick={() => toggle(t, tags, setTags)}>{tags.includes(t) && <Check size={14} />} {t}</button>)}</div>
        <p className="survey-selection">선택한 문화: {categories.join(', ')}</p>
      </fieldset>}
    </div>
    {error && <p className="form-error" role="alert">{error}</p>}
    <div className="survey-actions">{step === 1 && <button type="button" className="button outline" disabled={busy} onClick={() => move(0)}><ArrowLeft size={17} />이전</button>}<button className="button primary" disabled={!categories.length || busy}>{busy ? '저장 중…' : step === 0 ? '다음으로' : '취향 저장하기'}{step === 0 ? <ArrowRight size={17} /> : <Sparkles size={17} />}</button></div>
  </form>
}
