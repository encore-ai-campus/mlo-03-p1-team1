import { useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { ArrowUpRight, MapPin } from 'lucide-react'
import { CATEGORIES, REGIONS } from '../types'
import type { ContentPage } from '../types'
import { useApi } from '../hooks'
import { VenueMap } from '../components/VenueMap'
import type { MapArea } from '../components/VenueMap'
import { EmptyState, ErrorState, Loading } from '../components/States'
import { dateLabel } from '../components/ContentCard'

export function MapExplore(){
  const [params,setParams]=useSearchParams()
  const [area,setArea]=useState<MapArea|null>(null)
  const [selectedArea,setSelectedArea]=useState<MapArea|null>(null)
  const navigate=useNavigate()
  const query=new URLSearchParams(params);query.set('size','48');query.set('sort','ending')
  const result=useApi<ContentPage>(`/contents?${query}`)
  const items=useMemo(()=>result.data?.items||[],[result.data])
  const visible=items.filter(c=>!selectedArea||(c.latitude!=null&&c.longitude!=null&&!c.is_sample&&c.latitude>=selectedArea.south&&c.latitude<=selectedArea.north&&c.longitude>=selectedArea.west&&c.longitude<=selectedArea.east))
  const update=(key:string,value:string)=>{const next=new URLSearchParams(params);value?next.set(key,value):next.delete(key);next.delete('page');setParams(next);setSelectedArea(null)}
  return <div className="container page-content map-page"><div className="page-heading"><h1>장소로 둘러보기</h1><p>지역과 날짜를 고르고, 가까운 전시·공연을 찾아보세요.</p></div><div className="map-filters"><label>지역<select value={params.get('region')||''} onChange={e=>update('region',e.target.value)}><option value="">전국</option>{REGIONS.map(v=><option key={v}>{v}</option>)}</select></label><label>분야<select value={params.get('category')||''} onChange={e=>update('category',e.target.value)}><option value="">전체</option>{CATEGORIES.map(v=><option key={v}>{v}</option>)}</select></label><label>관람 시작일<input type="date" value={params.get('from_date')||''} onChange={e=>update('from_date',e.target.value)}/></label><label>관람 종료일<input type="date" min={params.get('from_date')||undefined} value={params.get('to_date')||''} onChange={e=>update('to_date',e.target.value)}/></label><Link className="text-link" to={`/explore?${params}`}>목록으로 보기<ArrowUpRight size={15}/></Link></div>
    {result.loading?<Loading/>:result.error?<ErrorState error={result.error} retry={result.retry}/>:<><div className="map-layout"><section><VenueMap contents={items} onOpen={id=>navigate(`/contents/${id}`)} onArea={setArea}/><div className="map-actions"><button className="button outline" disabled={!area} onClick={()=>setSelectedArea(area)}>현재 지도 영역에서 찾기</button>{selectedArea&&<button className="text-link" onClick={()=>setSelectedArea(null)}>영역 조건 해제</button>}</div><p className="sample-notice">위치가 확인된 실제 콘텐츠만 지도에 표시합니다. 현재 목록 최대 48개를 기준으로 표시합니다.</p></section><section className="venue-results"><h2>장소 목록 <span>{visible.length}건</span></h2>{visible.length?visible.map(c=><article key={c.id}><div className="card-meta"><span>{c.category}</span><span>{c.region}</span>{c.is_sample&&<span>샘플</span>}</div><Link to={`/contents/${c.id}`}><h3>{c.title}</h3></Link><p><MapPin size={14}/>{c.venue}</p><p>{c.address||'상세 주소는 주최 기관에서 확인해 주세요.'}</p><p>{dateLabel(c.start_date)} – {dateLabel(c.end_date)}</p>{!c.is_sample&&<a className="text-link" href={`https://map.kakao.com/link/search/${encodeURIComponent(c.address||c.venue)}`} target="_blank" rel="noreferrer">지도에서 보기<ArrowUpRight size={15}/></a>}</article>):<EmptyState title="이 영역에는 확인된 장소가 없어요" text="지도를 이동하거나 영역 조건을 해제해 주세요."/>}</section></div></>}
  </div>
}
