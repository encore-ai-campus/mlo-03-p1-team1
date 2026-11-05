import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import { useSession } from '../context'
import type { Content, ContentPage } from '../types'

export function useRecommendations(size = 8, enabled = true) {
  const { user, preferences, ready, revision } = useSession()
  const [data, setData] = useState<ContentPage | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(enabled)
  const [nonce, setNonce] = useState(0)
  const retry = useCallback(() => setNonce(value => value + 1), [])
  const categoriesKey = JSON.stringify(user ? [] : preferences?.categories || [])
  const tagsKey = JSON.stringify(user ? [] : preferences?.tags || [])
  const userId = user?.id

  useEffect(() => {
    if (!enabled || !ready) { setLoading(enabled); return }
    const abort = new AbortController()
    let active = true
    setLoading(true); setError(''); setData(null)
    const options = { signal: abort.signal }
    const categories: string[] = JSON.parse(categoriesKey)
    const tags = new Set<string>(JSON.parse(tagsKey))

    const load = async (): Promise<ContentPage> => {
      // Signed-in users keep the server's preference and activity based ranking.
      if (userId !== undefined || !categories.length) {
        return api<ContentPage>(`/recommendations?size=${size}`, options)
      }
      // Guest preferences stay in this browser; use the existing public catalog.
      const pages = await Promise.all([...new Set(categories)].map(category =>
        api<ContentPage>(`/contents?category=${encodeURIComponent(category)}&sort=popular&size=48`, options)))
      const candidates = [...new Map(pages.flatMap(page => page.items).map(content => [content.id, content])).values()]
      const score = (content: Content) => content.tags.filter(tag => tags.has(tag)).length
      const items = candidates.sort((a, b) => score(b) - score(a)).slice(0, size).map(content => {
        const tag = content.tags.find(value => tags.has(value))
        return { ...content, recommendation_reason: tag ? `관심 태그 #${tag}와 어울려요` : `선택한 ${content.category} 분야에서 골랐어요` }
      })
      return { items, total: items.length, page: 1, size }
    }

    load().then(result => { if (active) setData(result) }).catch((cause: unknown) => {
      if (active) setError(cause instanceof Error ? cause.message : '추천을 불러오지 못했어요.')
    }).finally(() => { if (active) setLoading(false) })
    return () => { active = false; abort.abort() }
  }, [enabled, ready, revision, userId, categoriesKey, tagsKey, size, nonce])

  return { data, error, loading, retry }
}
