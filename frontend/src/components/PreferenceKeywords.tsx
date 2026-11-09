import { useId, useState } from 'react'
import { Check, X } from 'lucide-react'
import { getKeywordGroups, KEYWORD_SECTIONS, MAX_PREFERENCE_TAGS } from '../preferenceKeywords'
import type { KeywordSectionId } from '../preferenceKeywords'
import '../styles/preference-keywords.css'

export function PreferenceKeywords({ categories, tags, onToggle }: {
  categories: string[]
  tags: string[]
  onToggle: (keyword: string) => void
}) {
  const [section, setSection] = useState<KeywordSectionId>('genre')
  const id = useId()
  const current = KEYWORD_SECTIONS.find(item => item.id === section)!
  const groups = getKeywordGroups(section, categories)
  const atLimit = tags.length >= MAX_PREFERENCE_TAGS

  return <div className="keyword-picker">
    <div className="keyword-selection-heading"><strong>선택한 키워드</strong><span role="status" aria-live="polite" aria-atomic="true">{tags.length} / {MAX_PREFERENCE_TAGS}개</span></div>
    <p className="keyword-selection-hint">{atLimit ? '다른 키워드를 고르려면 선택한 키워드를 먼저 해제해 주세요.' : '탭을 오가며 최대 10개까지 골라주세요. 선택하지 않아도 괜찮아요.'}</p>
    <div className="keyword-selected-list" aria-label="선택한 키워드">
      {tags.length ? tags.map(tag => <button type="button" className="tag selected keyword-selected" key={tag} aria-label={`${tag} 선택 해제`} onClick={() => onToggle(tag)}>{tag}<X size={13} aria-hidden="true" /></button>) : <span className="keyword-empty-selection">아래에서 나를 닮은 취향을 찾아보세요.</span>}
    </div>

    <div className="keyword-tabs" role="tablist" aria-label="키워드 분류">
      {KEYWORD_SECTIONS.map((item, index) => <button type="button" role="tab" key={item.id}
        id={`${id}-${item.id}-tab`} aria-controls={`${id}-panel`} aria-selected={section === item.id}
        tabIndex={section === item.id ? 0 : -1} onClick={() => setSection(item.id)}
        onKeyDown={event => {
          let next = index
          if (event.key === 'ArrowRight') next = (index + 1) % KEYWORD_SECTIONS.length
          else if (event.key === 'ArrowLeft') next = (index + KEYWORD_SECTIONS.length - 1) % KEYWORD_SECTIONS.length
          else if (event.key === 'Home') next = 0
          else if (event.key === 'End') next = KEYWORD_SECTIONS.length - 1
          else return
          event.preventDefault()
          setSection(KEYWORD_SECTIONS[next].id)
          document.getElementById(`${id}-${KEYWORD_SECTIONS[next].id}-tab`)?.focus()
        }}>{item.label}</button>)}
    </div>
    <div id={`${id}-panel`} role="tabpanel" aria-labelledby={`${id}-${section}-tab`} tabIndex={0}>
      <p className="keyword-section-description">{current.description}</p>
      {groups.map(group => <section className="keyword-group" key={group.id} aria-labelledby={`${id}-${group.id}`}>
        <h4 id={`${id}-${group.id}`}>{group.title}</h4>
        <div className="tag-choices">{group.keywords.map(keyword => {
          const selected = tags.includes(keyword)
          return <button type="button" className={selected ? 'tag selected' : 'tag'} key={keyword}
            aria-pressed={selected} disabled={!selected && atLimit} onClick={() => onToggle(keyword)}>
            {selected && <Check size={14} aria-hidden="true" />}{keyword}
          </button>
        })}</div>
      </section>)}
    </div>
  </div>
}
