import { RefreshCw, SearchX, LogIn } from 'lucide-react'
import { useSession } from '../context'

export function Loading() { return <div className="card-grid skeleton-grid" aria-label="콘텐츠를 불러오는 중" role="status">{[0, 1, 2, 3].map(i => <div key={i} className="skeleton"><div /><span /><span /></div>)}</div> }
export function ErrorState({ error, retry }: { error: string; retry: () => void }) { return <div className="empty-state" role="alert"><RefreshCw size={30} /><h3>콘텐츠를 불러오지 못했어요</h3><p>{error}</p><button className="button outline" onClick={retry}>다시 불러오기</button></div> }
export function EmptyState({ title = '조건에 맞는 콘텐츠가 없어요', text = '검색어나 필터를 바꿔 새로운 문화를 찾아보세요.', action }: { title?: string; text?: string; action?: () => void }) { return <div className="empty-state"><SearchX size={32} /><h3>{title}</h3><p>{text}</p>{action && <button className="button outline" onClick={action}>필터 초기화</button>}</div> }
export function LoginGate({ title }: { title: string }) { const s = useSession(); return <div className="empty-state login-gate"><LogIn size={36} /><h2>{title}</h2><p>로그인하고 나만의 문화생활을 이어가세요.</p><button className="button primary" onClick={s.openAuth}>로그인하기</button></div> }
