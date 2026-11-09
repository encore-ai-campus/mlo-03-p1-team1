import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Search, SlidersHorizontal, X } from 'lucide-react'
import { CATEGORIES } from '../types'
import type { ContentPage } from '../types'
import { useApi } from '../hooks'
import { track } from '../api/client'
import { ContentCard } from '../components/ContentCard'
import { EmptyState, ErrorState, Loading } from '../components/States'

export function Explore() {
  const [params, setParams] = useSearchParams()
  const [query, setQuery] = useState(params.get('q') || '')
  const [filtersOpen, setFiltersOpen] = useState(false)
  const input = useRef<HTMLInputElement>(null)
  const apiParams = new URLSearchParams(params); apiParams.delete('focus'); apiParams.set('size', '12')
  const result = useApi<ContentPage>(`/contents?${apiParams}`)
  const update = (key: string, value: string) => { const next = new URLSearchParams(params); value ? next.set(key, value) : next.delete(key); next.delete('page'); setParams(next); if (key !== 'q') void track('filter_use', undefined, key === 'category' ? value || undefined : undefined) }
  useEffect(() => { setQuery(params.get('q') || ''); if (params.get('focus') === 'search') input.current?.focus() }, [params])
  const page = Number(params.get('page') || 1)
  const activeCount = ['region', 'free_only', 'from_date', 'to_date', 'min_price', 'max_price'].filter(k => params.has(k)).length
  const filterLabels: Record<string, string> = { q: '검색', category: '분야', region: '지역', free_only: '가격', from_date: '시작일', to_date: '종료일', min_price: '최소 금액', max_price: '최대 금액' }
  const activeFilters = Object.entries(filterLabels).flatMap(([key, label]) => {
    const value = params.get(key)
    return value ? [{ key, label, value: key === 'free_only' ? '무료' : key.endsWith('price') ? `${Number(value).toLocaleString()}원` : value }] : []
  })
  const reset = () => { setParams({}); setQuery('') }
  return <div className="container page-content"><div className="page-heading"><span className="page-symbol">↗</span><h1>어떤 문화를 만나볼까요?</h1><p>익숙한 취향부터 새로운 발견까지, 나만의 문화 지도를 펼쳐보세요.</p></div>
    <form className="explore-search" role="search" onSubmit={e => { e.preventDefault(); update('q', query.trim()); void track('search') }}><Search size={23} aria-hidden="true" /><input ref={input} type="search" enterKeyHint="search" aria-label="검색어" value={query} onChange={e => setQuery(e.target.value)} maxLength={100} placeholder="전시, 공연 이름이나 공간을 검색하세요" />{query && <button type="button" className="icon-button" aria-label="검색어 지우기" onClick={() => { setQuery(''); update('q', '') }}><X size={18} /></button>}<button className="button primary">검색</button></form>
    <div className="explore-toolbar"><div className="pill-tabs" role="group" aria-label="분야별 필터">{['', ...CATEGORIES].map(c => <button key={c} aria-pressed={(params.get('category') || '') === c} className={(params.get('category') || '') === c ? 'active' : ''} onClick={() => update('category', c)}>{c || '전체'}</button>)}</div><button className={`filter-button ${filtersOpen || activeCount ? 'active' : ''}`} onClick={() => setFiltersOpen(!filtersOpen)} aria-expanded={filtersOpen} aria-controls="explore-filters"><SlidersHorizontal size={16} />상세 필터{activeCount > 0 && <span className="filter-count">{activeCount}</span>}</button></div>
    <div id="explore-filters" className="filter-panel" hidden={!filtersOpen}><label>지역<select value={params.get('region') || ''} onChange={e => update('region', e.target.value)}><option value="">전국</option>{['서울', '경기', '인천', '부산', '대구', '광주', '대전', '울산', '세종', '강원', '충북', '충남', '전북', '전남', '경북', '경남', '제주'].map(v => <option key={v}>{v}</option>)}</select></label><label>시작일<input type="date" value={params.get('from_date') || ''} onChange={e => update('from_date', e.target.value)} /></label><label>종료일<input type="date" min={params.get('from_date') || undefined} value={params.get('to_date') || ''} onChange={e => update('to_date', e.target.value)} /></label><label>최소 가격<input type="number" min="0" step="1000" value={params.get('min_price') || ''} onChange={e => update('min_price', e.target.value)} placeholder="제한 없음" /></label><label>최대 가격<input type="number" min={params.get('min_price') || '0'} step="1000" value={params.get('max_price') || ''} onChange={e => update('max_price', e.target.value)} placeholder="제한 없음" /></label><label className="checkbox-label"><input type="checkbox" checked={params.get('free_only') === 'true'} onChange={e => update('free_only', e.target.checked ? 'true' : '')} />무료만 보기</label><button className="text-link" onClick={reset}>모두 초기화</button></div>
    {activeFilters.length > 0 && <div className="active-filters" role="group" aria-label="적용된 검색 조건">{activeFilters.map(({ key, label, value }) => <button className="filter-token" key={key} aria-label={`${label}: ${value} 조건 해제`} onClick={() => update(key, '')}><span className="filter-token-label">{label}</span><span>{value}</span><X size={14} aria-hidden="true" /></button>)}<button className="clear-filters" onClick={reset}>모두 지우기</button></div>}
    <div className="results-bar"><p>{params.get('q') && <strong>‘{params.get('q')}’ </strong>}전체 <strong>{result.data?.total ?? '–'}</strong>개의 문화</p><Link to={`/map?${params}`} className="text-link">지도에서 보기</Link><label className="sort-label"><span className="sr-only">정렬</span><select value={params.get('sort') || 'latest'} onChange={e => update('sort', e.target.value)}><option value="latest">최근 수집순</option><option value="popular">찜 많은 순</option><option value="ending">종료 임박순</option></select></label></div>
    {result.loading ? <Loading /> : result.error ? <ErrorState error={result.error} retry={result.retry} /> : result.data?.items.length ? <><div className="card-grid">{result.data.items.map(c => <ContentCard key={`${c.id}-${c.bookmarked}`} content={c} />)}</div><div className="pagination"><button disabled={page <= 1} onClick={() => { const n = new URLSearchParams(params); n.set('page', String(page - 1)); setParams(n); window.scrollTo(0, 0) }} aria-label="이전 페이지"><ArrowLeft size={17} /></button><span>{page} / {Math.ceil(result.data.total / 12)}</span><button disabled={page * 12 >= result.data.total} onClick={() => { const n = new URLSearchParams(params); n.set('page', String(page + 1)); setParams(n); window.scrollTo(0, 0) }} aria-label="다음 페이지"><ArrowRight size={17} /></button></div></> : <EmptyState action={reset} />}
    {result.data?.items.some(c => c.is_sample) && <p className="sample-notice">‘샘플’은 가상 행사입니다. 실제 문화정보는 공개 API 수집 설정 후 제공됩니다.</p>}
  </div>
}
