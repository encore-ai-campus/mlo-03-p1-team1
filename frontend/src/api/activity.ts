const ANONYMOUS_KEY = 'culturepick.activity.anonymous'
const SESSION_KEY = 'culturepick.activity.session'
const PATH = /^\/(?:explore|recommendations|bookmarks|history|contents\/[1-9][0-9]*|mypage(?:\/(?:bookmarks|history|preferences|payments))?|payment\/result)?$/

function identifier(storage: Storage, key: string) {
  let value = storage.getItem(key)
  if (!value) { value = crypto.randomUUID(); storage.setItem(key, value) }
  return value
}

export function activityContext() {
  // No full URL, query string, auth token, user agent or IP in the event payload.
  return {
    anonymous_id: identifier(localStorage, ANONYMOUS_KEY),
    session_id: identifier(sessionStorage, SESSION_KEY),
    page_path: PATH.test(location.pathname) ? location.pathname : undefined,
  }
}

export type ClientEventType = 'page_view' | 'content_view' | 'search' | 'filter_use'
  | 'recommendation_click' | 'recommendation_impression' | 'payment_checkout_open'

export interface ActivityDetails {
  page_path?: string
  referrer_path?: string
  query_length?: number
  filter_name?: 'category' | 'region' | 'free_only' | 'sort' | 'from_date' | 'to_date' | 'reset'
  filter_value?: string
}
