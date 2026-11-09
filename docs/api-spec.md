# CulturePick API 계약

기본 경로 `/api/v1`. JSON, 날짜 `YYYY-MM-DD`, 시각 UTC ISO 8601, 금액 원화 정수. 자동 생성 OpenAPI(`/openapi.json`, `/docs`)가 필드 계약의 기준이며 `docs/openapi.json`은 생성한 스냅샷이다. `backend` 폴더에서 `python -m app.tasks.export_contract`로 갱신한다.

인증은 `Authorization: Bearer <token>`. 가입·로그인에서 발급하며 서버에는 SHA-256 해시만 저장한다. 세션은 7일 만료, 로그아웃 즉시 폐기. 브라우저는 sessionStorage에 보관한다. 운영은 HTTPS 필수. 인증 실패 401, 권한/정책 제한 403, 없는 자원 404, 상태 충돌 409, 입력 검증 422, 외부 서비스 실패 502, 설정/DB 미준비 503. 오류는 `{ "detail": "설명" }` 형식(입력 검증은 FastAPI의 detail 배열).

| 메서드 | 경로 | 동작 |
|---|---|---|
| GET | /health, /ready | 프로세스 / MariaDB 연결 상태 |
| POST | /auth/register, /auth/login | 회원 생성 / 세션 발급 |
| POST | /auth/logout | 현재 세션 폐기 |
| GET, PATCH | /users/me | 본인 프로필 조회 / 이름·성별·나이·거주지·직업·MBTI 부분 수정 |
| PUT | /surveys/me | categories, tags 설문 교체 |
| GET | /contents | q, category, region, free_only, from_date, to_date, sort, page, size 검색 |
| GET | /contents/{id} | 상세, 조회 자체는 상태 변경 없음 |
| GET | /contents/{id}/reviews | 리뷰 목록 |
| PUT, DELETE | /contents/{id}/reviews/me | 본인 리뷰 작성·수정 / 삭제 |
| GET | /bookmarks | 본인 찜 목록 |
| PUT, DELETE | /bookmarks/{content_id} | 멱등 찜 / 취소 |
| POST | /history/events | 본인 행동 이벤트 수집(event_id UUID 중복 무시) |
| GET | /history | 본인 최근 조회 콘텐츠 |
| GET | /recommendations | 공개 인기순 / 인증 시 취향·활동 기반 및 추천 이유 |
| GET | /payments/config | 현재 `enabled=true`, `mode=simulation`, `refunds_enabled=false` |
| POST | /payments/simulations | 로그인 사용자 모의 결제, UUID Idempotency-Key 필수, 성공 201 |
| GET | /payments/{payment_id} | 본인 주문 상세 조회, 외부 PG 호출·상태 변경 없음 |
| POST | /payments/orders | 서버 금액 산정, 고유 payment_id 발급, Idempotency-Key UUID 헤더 필수 |
| GET | /payments | 본인 주문·결제 이력 |
| POST | /payments/{payment_id}/verify | PortOne 재조회·검증 후 예약 확정 |
| POST | /payments/{payment_id}/cancel | 정책 활성화 시 전액 취소, 재조회·멱등 처리 |
| POST | /payments/webhook | Standard Webhooks 서명 검증·재조회, Bearer 불필요 |
| GET | /reservations | 본인 확정·취소 예약 |

목록 응답 `{items, total, page, size}`. 콘텐츠 검색 size 1–48, 페이지 1–1000. 추천 최대 24. 찜·조회 내역 최대 100. 결제/예약은 최대 100. 정렬 `latest`, `popular`, `ending`. 검색은 제목·장소 부분 일치이며 종료된 행사는 기본 제외(`include_ended=true`로 포함). 공급자 중복키 `(source, source_id)`.

모의 결제 입력은 `content_id` 양의 정수, `quantity` 정수 1–4(기본 1)이며 추가 필드는 422다. 서버 가격으로 금액을 계산하고 샘플도 허용한다. 무료/가격 미확인 콘텐츠 403, 종료 콘텐츠 409, 없는 콘텐츠 404. 성공 시 주문·결제 이력·이용 기록·분석 이벤트를 원자적으로 생성하고 `is_simulated=true`인 OrderOut을 반환한다. `/payments`와 `/reservations`에도 `is_simulated`가 포함된다. 같은 사용자·키의 재전송은 같은 기록을 반환하며 다른 상품/수량이면 409다. 실제 금액 청구나 PG 호출이 없다.

`/payments/orders`, verify/cancel/webhook은 기존 PortOne 경로이며 현재 프론트엔드에서 사용하지 않는다. 이 기존 경로만 샘플 실제 결제를 금지한다. 웹훅은 검증/트랜잭션 완료 후 반환하며 외부 장애 시 502로 재시도를 유도한다. 현재 사용하는 결제 명세는 [모의 결제](payment-spec.md)를 따른다.

인증 관련 요청은 프로세스당 IP 기준 1분 20회로 제한한다. 다중 Uvicorn worker 운영 시 공유 rate limiter 도입 필요. CORS는 명시 출처만 허용하며 Vite/Nginx 프록시를 사용하지 않는다.

## 프로필과 취향 설정

`GET /users/me`와 인증·설문 응답의 `user`에는 `gender`, `age`, `age_recorded_at`, `residence`, `occupation`, `mbti`가 포함된다. 기존 회원과 미입력 항목은 `null`이다. 이 정보는 본인 인증 응답에서만 제공하며 공개 리뷰·콘텐츠 응답에는 포함하지 않는다.

`PATCH /users/me`는 전달한 필드만 수정한다. `name`은 공백 제거 후 2–40자이며 `null`로 지울 수 없다. 나머지 입력 항목은 `null`로 삭제할 수 있다. 이메일·회원 ID·설문 완료 여부 등 허용하지 않은 필드를 전달하면 422다.

| 필드 | 입력 형식 |
|---|---|
| gender | `female`, `male`, `other`, `prefer_not_to_say` 중 하나 또는 `null` |
| age | 만 나이 정수 0–120 또는 `null`. 문자열·소수·불리언 불허 |
| residence | 서울, 부산, 대구, 인천, 광주, 대전, 울산, 세종, 경기, 강원, 충북, 충남, 전북, 전남, 경북, 경남, 제주, 해외 중 하나 또는 `null` |
| occupation | 앞뒤 공백 제거 후 최대 80자 또는 `null`. 빈 문자열은 `null` |
| mbti | 16개 MBTI 코드 또는 `null`. 소문자·앞뒤 공백은 정규화하고 빈 문자열은 `null` |

`age_recorded_at`은 나이를 입력한 UTC 시각이며 서버가 관리한다. 이름 등 다른 항목만 바꾸면 유지하고 나이를 삭제하면 함께 삭제한다. 나이는 이 시각에 입력한 값으로, 자동으로 증가하지 않는다.

프론트엔드는 회원가입 성공 직후에만 초기 취향 설문을 자동 표시한다. 로그인과 세션 복원 시에는 설문 미완료 여부와 관계없이 자동 표시하지 않는다. 이후 설정·수정은 `/mypage/preferences`에서 `PUT /surveys/me`로 처리하며 같은 프로필을 유지한다. `/mypage`의 기본 페이지는 나의 정보이고 찜·최근 조회·취향·이용 및 결제 내역은 각각 별도 경로를 사용한다.
