export const CATEGORIES = ['전시', '뮤지컬', '연극', '음악', '무용', '축제'] as const
export type Category = typeof CATEGORIES[number]
export const GENDERS = { female: '여성', male: '남성', other: '기타', prefer_not_to_say: '응답하지 않음' } as const
export const RESIDENCES = ['서울', '부산', '대구', '인천', '광주', '대전', '울산', '세종', '경기', '강원', '충북', '충남', '전북', '전남', '경북', '경남', '제주', '해외'] as const
export const MBTI_TYPES = ['ISTJ', 'ISFJ', 'INFJ', 'INTJ', 'ISTP', 'ISFP', 'INFP', 'INTP', 'ESTP', 'ESFP', 'ENFP', 'ENTP', 'ESTJ', 'ESFJ', 'ENFJ', 'ENTJ'] as const
export interface User {
  id: number; email: string; name: string; categories: string[]; tags: string[]; survey_completed: boolean;
  gender: keyof typeof GENDERS | null; age: number | null; age_recorded_at: string | null;
  residence: typeof RESIDENCES[number] | null; occupation: string | null; mbti: string | null;
}
export interface Content {
  id: number; title: string; subtitle: string; category: string; region: string; venue: string; address: string;
  start_date: string; end_date: string; price: number; price_text: string; description: string; image_url: string;
  source: string; source_url: string; tags: string[]; is_sample: boolean; bookable: boolean;
  collected_at: string; bookmarked: boolean; rating: number | null; review_count: number; recommendation_reason: string | null;
}
export interface ContentPage { items: Content[]; total: number; page: number; size: number }
export interface Review { id: number; user_id: number; name: string; rating: number; body: string; updated_at: string }
export interface Order { payment_id: string; content_id: number; order_name: string; quantity: number; amount: number; cancelled_amount: number; currency: string; status: string; is_simulated: boolean; created_at: string }
export interface Reservation { id: number; payment_id: string; content_id: number; title: string; venue: string; start_date: string; status: string; quantity: number; amount: number; is_simulated: boolean }
export interface PaymentConfig { enabled: boolean; mode: 'simulation'; refunds_enabled: boolean; store_id: string; channel_key: string }
