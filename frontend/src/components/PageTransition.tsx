import { useLayoutEffect, useRef } from 'react'
import type { ReactNode } from 'react'
import { useLocation } from 'react-router-dom'
import { createSpring } from '../motion'

export function PageTransition({ children }: { children: ReactNode }) {
  const { pathname } = useLocation()
  const ref = useRef<HTMLDivElement>(null)
  const spring = useRef<ReturnType<typeof createSpring> | null>(null)

  useLayoutEffect(() => {
    const element = ref.current!
    spring.current = createSpring([0, 1], ([y, opacity]) => {
      element.style.translate = `0 ${y}px`
      element.style.opacity = String(opacity)
    }, .36)
    const reduced = matchMedia('(prefers-reduced-motion: reduce)')
    const handleMotionChange = () => { if (reduced.matches) spring.current?.jump([0, 1]) }
    reduced.addEventListener('change', handleMotionChange)
    return () => { spring.current?.stop(); reduced.removeEventListener('change', handleMotionChange) }
  }, [])

  useLayoutEffect(() => {
    const animation = spring.current!
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) { animation.jump([0, 1]); return }
    // Keep navigation interactive, including a second navigation mid-transition.
    if (!animation.running) animation.jump([12, .65])
    animation.to([0, 1])
  }, [pathname])

  return <div ref={ref} className="route-surface">{children}</div>
}
