import { useApi } from '../hooks'
import { useSession } from '../context'
import { EmptyState, ErrorState, Loading, LoginGate } from '../components/States'

interface Overview { counts: Record<string,number>; categories: {name:string;count:number}[]; activities:{name:string;count:number}[]; runs:{id:number;started_at:string;finished_at:string|null;status:string;collected_count:number;error_code:string}[] }
const activityLabels: Record<string,string> = { content_view:'콘텐츠 조회', bookmark_add:'찜 추가', bookmark_remove:'찜 해제', search:'검색', filter_use:'필터 사용', recommendation_click:'추천 클릭', recommendation_impression:'추천 노출' }
export function Admin() {
  const s = useSession()
  const data = useApi<Overview>(s.user?.is_admin ? '/admin/overview' : null)
  return <div className="container page-content"><div className="page-heading"><h1>운영 현황</h1><p>콘텐츠 수집과 서비스 활동의 실제 집계입니다.</p></div>
    {!s.ready ? <Loading /> : !s.user ? <LoginGate title="관리자 계정으로 로그인해 주세요" /> : !s.user.is_admin ? <EmptyState title="관리 권한이 필요합니다" text="권한이 있는 계정으로 로그인해 주세요." /> : data.loading ? <Loading /> : data.error ? <ErrorState error={data.error} retry={data.retry} /> : data.data && <>
      <div className="admin-summary">{Object.entries({contents:'콘텐츠',members:'회원',bookmarks:'찜',reviews:'리뷰',events:'활동 기록'}).map(([key,label])=><div key={key}><span>{label}</span><strong>{data.data!.counts[key].toLocaleString()}</strong></div>)}</div>
      <div className="admin-breakdowns"><section><h2>분야별 콘텐츠</h2>{data.data.categories.map(v=><div className="metric-row" key={v.name}><span>{v.name}</span><strong>{v.count.toLocaleString()}건</strong></div>)}</section><section><h2>활동별 적재 현황</h2>{data.data.activities.length ? data.data.activities.map(v=><div className="metric-row" key={v.name}><span>{activityLabels[v.name]||v.name}</span><strong>{v.count.toLocaleString()}건</strong></div>) : <p className="muted">아직 기록된 활동이 없습니다.</p>}</section></div>
      <div className="section-heading"><h2>최근 수집 실행</h2><button className="text-link" onClick={data.retry}>새로고침</button></div>
      {data.data.runs.length ? <div className="data-table-wrap"><table className="data-table"><thead><tr><th>시작 시각</th><th>상태</th><th>수집 건수</th><th>오류 유형</th></tr></thead><tbody>{data.data.runs.map(r=><tr key={r.id}><td>{new Date(r.started_at).toLocaleString('ko-KR')}</td><td>{({SUCCESS:'성공',FAILED:'실패',RUNNING:'실행 중'} as Record<string,string>)[r.status]||r.status}</td><td>{r.collected_count}건</td><td>{r.error_code||'—'}</td></tr>)}</tbody></table></div> : <EmptyState title="아직 수집 실행 기록이 없습니다" text="외부 데이터 수집 작업을 실행하면 결과가 표시됩니다." />}
    </>}
  </div>
}
