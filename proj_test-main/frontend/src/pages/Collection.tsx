import { useEffect, useRef } from 'react'
import { Bookmark, Clock3, SlidersHorizontal } from 'lucide-react'
import { useSession } from '../context'
import { useApi } from '../hooks'
import { track } from '../api/client'
import type { ContentPage } from '../types'
import { ContentCard } from '../components/ContentCard'
import { EmptyState, ErrorState, Loading, LoginGate } from '../components/States'
import { Link } from 'react-router-dom'

export function Collection({ kind }: { kind: 'recommendations' | 'bookmarks' | 'history' | 'visits' }) {
  const s = useSession()
  const rec = kind === 'recommendations'
  const config = rec ? { title: '취향에 맞는 전시와 공연', text: '관심 분야와 활동을 바탕으로 고른 문화 소식입니다.', Icon: SlidersHorizontal } : kind === 'bookmarks' ? { title: '마음에 담은 문화', text: '언젠가의 문화생활을 위해 모아둔 순간들.', Icon: Bookmark } : kind === 'visits' ? { title: '관람한 문화', text: '상세 화면에서 직접 관람 완료로 등록한 기록입니다.', Icon: Clock3 } : { title: '최근 둘러본 문화', text: '잠시 눈길이 머물렀던 문화 콘텐츠를 다시 만나세요.', Icon: Clock3 }
  const result = useApi<ContentPage>(s.user || rec ? `/${kind}${rec ? '?size=24' : ''}` : null)
  const seen = useRef(new Set<number>())
  useEffect(() => { if (rec && result.data) for (const c of result.data.items) if (!seen.current.has(c.id)) { seen.current.add(c.id); void track('recommendation_impression', c.id) } }, [rec, result.data])
  if (!s.ready) return <div className="container page-content"><Loading /></div>
  if (!s.user && !rec) return <div className="container page-content"><LoginGate title={`${kind === 'bookmarks' ? '찜한' : '최근 본'} 문화를 모아보세요`} /></div>
  return <div className="container page-content"><div className="page-heading"><config.Icon className="page-symbol" size={36} /><h1>{config.title}</h1><p>{config.text}</p></div>
    {rec && <div className="preference-summary"><div><SlidersHorizontal size={20} /><span>{s.user?.survey_completed ? `관심 분야: ${s.user.categories.join(', ')}` : '나의 취향을 알려주면 추천이 더 가까워져요.'}</span></div><button className="text-link" onClick={s.openSurvey}>취향 {s.user?.survey_completed ? '수정' : '설정'}하기</button></div>}
    {result.loading ? <Loading /> : result.error ? <ErrorState error={result.error} retry={result.retry} /> : result.data?.items.length ? <div className="card-grid">{result.data.items.map(c => <ContentCard key={`${c.id}-${c.bookmarked}`} content={c} recommended={rec} />)}</div> : <><EmptyState title={kind === 'bookmarks' ? '아직 마음에 담은 문화가 없어요' : kind === 'history' ? '아직 둘러본 문화가 없어요' : '추천할 콘텐츠를 기다리고 있어요'} text="문화 탐색에서 마음이 끌리는 콘텐츠를 만나보세요." /><div className="center"><Link className="button primary" to="/explore">문화 탐색하기</Link></div></>}
  </div>
}
