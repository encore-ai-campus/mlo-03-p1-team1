import type { User } from './types'

export type TastePreferences = Pick<User, 'categories' | 'tags'>

const PREFERENCES_KEY = 'culturepick.preferences'
const ONBOARDING_DISMISSED_KEY = 'culturepick.onboarding.dismissed'

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every(item => typeof item === 'string')
}

export function readPreferences(): TastePreferences | null {
  try {
    const value: unknown = JSON.parse(localStorage.getItem(PREFERENCES_KEY) || 'null')
    if (!value || typeof value !== 'object') return null
    const preferences = value as Record<string, unknown>
    if (!isStringArray(preferences.categories) || !isStringArray(preferences.tags)) return null
    return { categories: preferences.categories, tags: preferences.tags }
  } catch {
    // Invalid saved data or unavailable storage must allow the app to start.
    return null
  }
}

export function storePreferences(preferences: TastePreferences): void {
  try {
    localStorage.setItem(PREFERENCES_KEY, JSON.stringify({ categories: preferences.categories, tags: preferences.tags }))
  } catch {
    // SessionProvider keeps the current selection in memory if storage is blocked.
  }
}

export function onboardingDismissed(): boolean {
  try {
    return localStorage.getItem(ONBOARDING_DISMISSED_KEY) === 'true'
  } catch {
    return false
  }
}

export function dismissOnboarding(): void {
  try {
    localStorage.setItem(ONBOARDING_DISMISSED_KEY, 'true')
  } catch {
    // SessionProvider also tracks dismissal for the current page session.
  }
}
