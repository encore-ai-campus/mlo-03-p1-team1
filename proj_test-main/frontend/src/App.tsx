import { useEffect } from 'react'
import { Link, Route, Routes, useLocation } from 'react-router-dom'
import { SessionProvider } from './context'
import { Layout } from './components/Layout'
import { Home } from './pages/Home'
import { Explore } from './pages/Explore'
import { Collection } from './pages/Collection'
import { Detail } from './pages/Detail'
import { MyPage } from './pages/MyPage'
import { PaymentResult } from './pages/PaymentResult'
import { MyReviews } from './pages/MyReviews'
import { MapExplore } from './pages/MapExplore'
import { Admin } from './pages/Admin'

export default function App() {
  const { pathname } = useLocation()
  useEffect(() => { window.scrollTo({ top: 0 }); document.title = 'Oddinary 오디너리 · 일상과 예술 사이' }, [pathname])
  return <SessionProvider><Routes><Route element={<Layout />}><Route index element={<Home />} /><Route path="explore" element={<Explore />} /><Route path="map" element={<MapExplore />} /><Route path="contents/:id" element={<Detail />} /><Route path="recommendations" element={<Collection kind="recommendations" />} /><Route path="bookmarks" element={<Collection kind="bookmarks" />} /><Route path="history" element={<Collection kind="history" />} /><Route path="visits" element={<Collection kind="visits" />} /><Route path="my-reviews" element={<MyReviews />} /><Route path="admin" element={<Admin />} /><Route path="mypage" element={<MyPage />} /><Route path="payment/result" element={<PaymentResult />} /><Route path="*" element={<div className="container page-content empty-state"><h1>페이지를 찾을 수 없어요</h1><Link className="button primary" to="/">발견하기로 돌아가기</Link></div>} /></Route></Routes></SessionProvider>
}
