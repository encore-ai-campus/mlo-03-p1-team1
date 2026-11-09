import { useEffect, useRef } from 'react'
import { useLocation } from 'react-router-dom'
import { activityContext } from '../api/activity'
import { track } from '../api/client'

export function ActivityTracker() {
  const location = useLocation()
  const previous = useRef<{ key: string; path?: string } | null>(null)
  useEffect(() => {
    if (previous.current?.key === location.key) return
    let path: string | undefined
    try { path = activityContext().page_path } catch { return }
    const referrer = previous.current?.path
    previous.current = { key: location.key, path }
    if (path) void track('page_view', undefined, undefined, { page_path: path, referrer_path: referrer })
  }, [location.key, location.pathname])
  return null
}
