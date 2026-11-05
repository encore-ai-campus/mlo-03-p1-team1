import { useEffect, useRef, useState } from 'react'
import { MapPin } from 'lucide-react'
import type { Content } from '../types'

interface Point { getLat():number; getLng():number }
interface Bounds { extend(point:Point):void; getSouthWest():Point; getNorthEast():Point }
interface MapInstance { setBounds(bounds:Bounds):void; getBounds():Bounds; relayout():void }
interface Marker { setMap(map:MapInstance|null):void }
interface Maps {
  load(callback:()=>void):void
  LatLng:new(lat:number,lng:number)=>Point
  LatLngBounds:new()=>Bounds
  Map:new(element:HTMLElement,options:{center:Point;level:number})=>MapInstance
  Marker:new(options:{map:MapInstance;position:Point;title:string})=>Marker
  event:{ addListener(target:MapInstance|Marker,name:string,callback:()=>void):void; removeListener(target:MapInstance|Marker,name:string,callback:()=>void):void }
}
declare global { interface Window { kakao?:{maps:Maps} } }
export interface MapArea { south:number;west:number;north:number;east:number }
let sdk:Promise<Maps>|null = null
function loadMaps() {
  if (sdk) return sdk
  const key = import.meta.env.VITE_KAKAO_MAP_APP_KEY
  if (!key) return Promise.reject(new Error('Map is not configured'))
  sdk = new Promise<Maps>((resolve,reject)=>{
    const timer = window.setTimeout(()=>reject(new Error('Map request timed out')),15000)
    const ready=()=>window.kakao?.maps.load(()=>{window.clearTimeout(timer);resolve(window.kakao!.maps)})
    if(window.kakao?.maps){ready();return}
    const script=document.createElement('script')
    script.src=`https://dapi.kakao.com/v2/maps/sdk.js?appkey=${encodeURIComponent(key)}&autoload=false`
    script.async=true;script.onload=ready;script.onerror=()=>{window.clearTimeout(timer);reject(new Error('Map unavailable'))};document.head.append(script)
  })
  sdk.catch(()=>{sdk=null})
  return sdk
}

export function VenueMap({contents,onOpen,onArea}:{contents:Content[];onOpen:(id:number)=>void;onArea:(area:MapArea)=>void}) {
  const container=useRef<HTMLDivElement>(null)
  const [status,setStatus]=useState<'loading'|'ready'|'error'>('loading')
  const callbacks=useRef({onOpen,onArea});callbacks.current={onOpen,onArea}
  useEffect(()=>{
    let active=true
    const cleanups:(()=>void)[]=[]
    setStatus('loading')
    loadMaps().then(maps=>{
      if(!active||!container.current)return
      const valid=contents.filter(c=>c.latitude!=null&&c.longitude!=null&&!c.is_sample)
      const map=new maps.Map(container.current,{center:new maps.LatLng(37.5665,126.978),level:8})
      const bounds=new maps.LatLngBounds()
      valid.forEach(c=>{
        const position=new maps.LatLng(c.latitude!,c.longitude!);bounds.extend(position)
        const marker=new maps.Marker({map,position,title:`${c.title} · ${c.venue}`})
        const click=()=>callbacks.current.onOpen(c.id)
        maps.event.addListener(marker,'click',click)
        cleanups.push(()=>{maps.event.removeListener(marker,'click',click);marker.setMap(null)})
      })
      if(valid.length)map.setBounds(bounds)
      const report=()=>{const b=map.getBounds(),sw=b.getSouthWest(),ne=b.getNorthEast();callbacks.current.onArea({south:sw.getLat(),west:sw.getLng(),north:ne.getLat(),east:ne.getLng()})}
      maps.event.addListener(map,'idle',report);cleanups.push(()=>maps.event.removeListener(map,'idle',report));report()
      const observer=new ResizeObserver(()=>map.relayout());observer.observe(container.current);cleanups.push(()=>observer.disconnect())
      setStatus('ready')
    }).catch(()=>{if(active)setStatus('error')})
    return()=>{active=false;cleanups.forEach(f=>f());container.current?.replaceChildren()}
  },[contents])
  return <div className="venue-map-shell"><div className="venue-map" ref={container} aria-label="문화 콘텐츠 개최 장소 지도" />{status!=='ready'&&<div className="map-status" role="status"><MapPin size={28}/><h2>{status==='loading'?'지도를 불러오는 중입니다':'지도를 불러올 수 없습니다'}</h2><p>{status==='error'?'목록의 ‘지도에서 보기’로 장소를 확인할 수 있습니다.':'잠시만 기다려 주세요.'}</p></div>}</div>
}
