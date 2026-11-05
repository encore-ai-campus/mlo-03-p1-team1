# 데이터 사전

| 테이블 | 주요 필드 | 의미 |
|---|---|---|
| users | id, email, name, password_hash | 이메일 소문자 정규화·유일, scrypt 개별 salt |
| users | categories, tags, survey_completed | 현재 설문 JSON 배열과 완료 여부 |
| auth_sessions | token_hash, user_id, expires_at | 원본 토큰 저장 금지, 7일 만료 |
| contents | source, source_id | 공급자별 중복 식별자 |
| contents | category, region, title, venue, address | 검색·표시 데이터, 표준 6개 분야 |
| contents | start_date, end_date | 한국 현지 행사 날짜 |
| contents | price, price_text | 내부 판매 정수 금액 / 외부 요금 설명. price=0만으로 무료 판단 금지 |
| contents | is_sample, bookable | 가상 여부 / 내부 판매 가능 여부, 샘플 판매 절대 금지 |
| contents | image_url, source_url, collected_at | 포스터·공식 링크·최근 수집 시각 |
| bookmarks | user_id, content_id, created_at | 현재 찜 상태 (복합 PK) |
| reviews | user_id, content_id, rating, body, updated_at | 회원당 콘텐츠당 1개, 1–5점, 5–2000자 |
| behavior_events | event_id, event_type, user_id, content_id, occurred_at, properties | 이벤트 원본, [계약](event-contract.md) 참조 |
| orders | payment_id, user_id, content_id, idempotency_key | 서버 발급 UUID 주문, 소유권·요청 멱등성 |
| orders | order_name, quantity, amount, currency | 생성 시 고정한 주문명·수량·금액(KRW). 클라이언트 금액 불수신 |
| orders | status, cancelled_amount, updated_at | 검증한 현재 결제 상태·누적 취소액 |
| payment_history | payment_id, status, amount, cancelled_amount, provider_transaction_id | 검증된 상태 변화 시 주문 원금·누적 취소액 스냅샷·PG 거래 식별자 |
| reservations | payment_id, user_id, content_id, status | PAID 검증 후 1건, CONFIRMED/CANCELLED/REVIEW_REQUIRED |
| webhook_receipts | event_id, payment_id, received_at | 처리된 서명 웹훅 중복 식별자 |

모든 정수 PK는 MariaDB AUTO_INCREMENT. 날짜는 DATE, 시각은 UTC DATETIME이며 API는 UTC `Z` 표기로 내보낸다. 가격은 원화 정수이고 소수·음수 주문을 허용하지 않는다. 참조 SQL 및 인덱스는 database/mariadb에 둔다.
