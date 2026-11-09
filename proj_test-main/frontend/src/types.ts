export const CATEGORIES = ['전시', '뮤지컬', '연극', '음악', '무용', '축제'] as const
export type Category = typeof CATEGORIES[number]
export const REGIONS = ['서울','경기','인천','부산','대구','광주','대전','울산','세종','강원','충북','충남','전북','전남','경북','경남','제주'] as const
export interface Preferences { regions: string[]; max_price: number | null; companions: string[] }
export interface User { id: number; email: string; name: string; categories: string[]; tags: string[]; survey_completed: boolean; preferences: Preferences; is_admin: boolean }
export interface Content {
  id: number; title: string; subtitle: string; category: string; region: string; venue: string; address: string;
  start_date: string; end_date: string; price: number; price_text: string; description: string; image_url: string;
  latitude: number | null; longitude: number | null;
  source: string; source_url: string; tags: string[]; is_sample: boolean; bookable: boolean;
  collected_at: string; bookmarked: boolean; rating: number | null; review_count: number; recommendation_reason: string | null;
}
export interface ContentPage { items: Content[]; total: number; page: number; size: number }
export interface Review { id: number; user_id: number; name: string; rating: number; body: string; updated_at: string }
export interface UserReview extends Review { content_id: number; content_title: string }
export interface Order { payment_id: string; content_id: number; order_name: string; quantity: number; amount: number; cancelled_amount: number; currency: string; status: string; created_at: string }
export interface Reservation { id: number; payment_id: string; content_id: number; title: string; venue: string; start_date: string; status: string; quantity: number; amount: number }
export interface PaymentConfig { enabled: boolean; refunds_enabled: boolean; store_id: string; channel_key: string }
