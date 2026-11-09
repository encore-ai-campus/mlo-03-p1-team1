import { useEffect } from 'react'
import { createSpring } from '../motion'

const INTERACTIVE = 'button, a.button, a.icon-button, a.text-link, nav a, .home-categories a, .content-card, .home-art-poster'

export function useAppleInteractions() {
  useEffect(() => {
    const reduced = matchMedia('(prefers-reduced-motion: reduce)')
    const finePointer = matchMedia('(hover: hover) and (pointer: fine)')
    type Interaction = { hovered: boolean; pressed: boolean; spring: ReturnType<typeof createSpring> }
    const states = new Map<HTMLElement, Interaction>()
    const refresh = (element: HTMLElement, state: Interaction) => {
      const card = element.matches('.content-card, .home-art-poster')
      const target = reduced.matches ? [0, 1] : state.pressed ? [0, card ? .985 : .96] : state.hovered ? [card ? -5 : -1.5, card ? 1.008 : 1.025] : [0, 1]
      if (reduced.matches) state.spring.jump(target)
      else state.spring.to(target)
    }
    const stateFor = (element: HTMLElement) => {
      let state = states.get(element)
      if (!state) {
        state = { hovered: false, pressed: false, spring: createSpring([0, 1], ([y, scale]) => {
          element.style.translate = `0 ${y}px`
          element.style.scale = String(scale)
        }) }
        states.set(element, state)
      }
      return state
    }
    const hover = (event: PointerEvent, hovered: boolean) => {
      if (!finePointer.matches || event.pointerType === 'touch') return
      let element = event.target instanceof Element ? event.target.closest<HTMLElement>(INTERACTIVE) : null
      while (element) {
        if (!(event.relatedTarget instanceof Node && element.contains(event.relatedTarget)) && !element.matches(':disabled')) {
          const state = stateFor(element)
          state.hovered = hovered
          if (!hovered) state.pressed = false
          refresh(element, state)
        }
        element = element.parentElement?.closest<HTMLElement>(INTERACTIVE) || null
      }
    }
    const over = (event: PointerEvent) => hover(event, true)
    const out = (event: PointerEvent) => hover(event, false)
    const down = (event: PointerEvent) => {
      if (event.button !== 0) return
      const element = event.target instanceof Element ? event.target.closest<HTMLElement>(INTERACTIVE) : null
      if (!element || element.matches(':disabled')) return
      const state = stateFor(element)
      state.pressed = true
      refresh(element, state)
    }
    const release = () => states.forEach((state, element) => {
      if (state.pressed) { state.pressed = false; refresh(element, state) }
    })
    const reset = () => states.forEach((state, element) => {
      state.hovered = false; state.pressed = false; refresh(element, state)
    })
    // Disconnected cards are released after navigation or a filter replaces a list.
    const observer = new MutationObserver(() => states.forEach((state, element) => {
      if (!element.isConnected) { state.spring.stop(); states.delete(element) }
    }))
    observer.observe(document.body, { childList: true, subtree: true })
    document.addEventListener('pointerover', over)
    document.addEventListener('pointerout', out)
    document.addEventListener('pointerdown', down)
    document.addEventListener('pointerup', release)
    document.addEventListener('pointercancel', reset)
    window.addEventListener('blur', reset)
    reduced.addEventListener('change', reset)
    return () => {
      observer.disconnect()
      document.removeEventListener('pointerover', over)
      document.removeEventListener('pointerout', out)
      document.removeEventListener('pointerdown', down)
      document.removeEventListener('pointerup', release)
      document.removeEventListener('pointercancel', reset)
      window.removeEventListener('blur', reset)
      reduced.removeEventListener('change', reset)
      states.forEach((state, element) => { state.spring.stop(); element.style.removeProperty('translate'); element.style.removeProperty('scale') })
    }
  }, [])
}
