# 행동 이벤트 계약 v2

2026-11-06 사용자 요청에 따라 분석용 이벤트를 MongoDB **`oddinary.user_events`**에 적재한다. MariaDB `behavior_events`는 추천/최근 조회를 위해 유지하며 `event_outbox`로 커밋된 이벤트만 MongoDB에 전달한다. 회원·찜·리뷰·주문·결제·예약의 기준은 계속 MariaDB다. 이벤트로 실제 업무 상태를 대체하거나 재구성하지 않는다.

공통 필드: `event_id` UUID 문자열 PK, `event_type` 문자열, `user_id` 인증 토큰으로 결정(비로그인 null), `content_id` 해당 시 FK, `occurred_at` 서버 수신 UTC 시각, `properties` 허용된 부가 정보만 저장하는 JSON. 브라우저는 user_id나 occurred_at을 제출할 수 없다. MongoDB의 문서 스키마 버전은 1이며 이 계약 문서의 v2와 구분한다.

| 이벤트 | 생성 주체 | 용도 |
|---|---|---|
| page_view | React Router 초기 화면/경로/query 이동 | 안전한 page_path와 referrer_path. 전체 URL은 저장하지 않음 |
| content_view | 상세 데이터 로드 성공, 회원/비회원 | 최근 조회, 회원의 시간감쇠 추천 점수 1 |
| recommendation_click | 추천 카드 클릭 | 시간감쇠 추천 점수 2 |
| recommendation_impression | 추천 페이지의 콘텐츠 목록 | 추천 노출 분석, 점수에는 미반영 |
| search | 검색 제출 | 검색 횟수 분석. 원문 대신 query_length(0–100)만 저장 |
| filter_use | 탐색 필터 변경/초기화 | category, filter_name, filter_value |
| bookmark_add / bookmark_remove | 찜 API 서버 | 실제 상태와 같은 DB 트랜잭션의 행동 기록 |
| payment_completed | 모의 결제 API 서버 | 콘텐츠 선택·결제 행동 분석. 주문·결제 이력·이용 기록과 같은 트랜잭션에서 한 번 생성 |
| payment_checkout_open | 결제 확인 화면 열기 | content_id 필수. 완료 이벤트가 아님 |
| payment_cancelled | PortOne 서버 검증으로 취소 상태 변경 확인 | 결제 요약과 cancelled_amount. 브라우저 제출 불가 |

`payment_completed`의 properties는 `payment_id`, `payment_mode`, `quantity`, `amount`, `currency`다. 현재 화면의 모의 결제는 `payment_mode=simulation`이며 실제 청구/관람이 아닌 선택 데이터다. 기존 PortOne 경로도 결제 상태/금액을 재검증하여 상태가 변경된 경우에만 `payment_mode=portone_v2`를 생성한다. 서버만 생성하며 브라우저 이벤트 수집 API로 직접 제출할 수 없다. 동일 주문 요청 재전송은 이벤트를 추가하지 않는다.

추천 노출은 추천 페이지 목록이 렌더링된 기준이며 실제 viewport 교차/시야 체류 보장은 하지 않는다. 비로그인 활동도 익명/세션 UUID로 수집하지만 공개 추천을 사용한다. 동일 event_id 재전송은 첫 저장만 인정하며 payload 덮어쓰기나 사용자 변경을 하지 않는다.

찜 상태 PUT/DELETE는 멱등이지만 각 요청을 행동 시도로 기록한다. 추천 점수에는 현재 찜 상태만 사용하여 중복 요청으로 점수가 부풀지 않는다. 조회/클릭은 콘텐츠·종류·한국/UTC 날짜 중 현재 구현의 UTC 수신일 기준 일 1회만 점수에 반영한다. 30일 지수 감쇠, 회원당 최근 500개 이벤트가 계산 대상이다. 행동 수집 실패는 탐색 UI를 막지 않는다.

이벤트에는 이메일·이름·비밀번호·카드번호·IP·PG 비밀키·인증 토큰·인증 응답·전체 URL을 넣지 않는다. 운영 보존 기간/동의/삭제 정책은 팀에서 확정해야 하며 임의 TTL 삭제 작업은 추가하지 않았다.

## MongoDB 문서 스키마

실제 적용 파일: [`database/mongodb/user_events.schema.json`](../database/mongodb/user_events.schema.json). strict/error validator, `_id == event_id` 검증, event_id unique 인덱스를 사용한다.

| 필드 | BSON 형식 | 의미 |
| --- | --- | --- |
| `_id`, `event_id` | UUID 문자열 | 동일 값. 재전송/재처리 중복 기준 |
| `schema_version` | int, 1 | Mongo 문서 버전 |
| `event_type` | enum 문자열 | 위 표의 활동 종류 |
| `user_id` | int 또는 null | 서버 인증으로 결정한 MariaDB 회원 ID |
| `anonymous_id` | UUID 문자열 또는 null | localStorage 임의 브라우저 ID. 신원 확인 수단이 아님 |
| `session_id` | UUID 문자열 또는 null | sessionStorage의 탭 활동 ID. 인증 토큰이 아님 |
| `content_id` | int 또는 null | 해당 콘텐츠 식별자 |
| `occurred_at` | BSON Date, UTC | FastAPI가 수락한 시각. 클라이언트 시계를 사용하지 않음 |
| `ingested_at` | BSON Date, UTC | MongoDB 최초 적재 시각. 재처리 시 유지 |
| `source` | browser / server | 화면에서 생성했는지 서버 업무 처리에서 생성했는지 구분 |
| `page_path`, `referrer_path` | pathname 또는 null | 알려진 앱 경로만. 도메인/query/fragment 제외 |
| `properties` | 허용된 키의 object | 분야, 검색어 길이, 필터, 서버 결제 요약 |

## API 입력과 인증

`POST /api/v1/history/events` → 202 `{"accepted": true}`. 이는 MariaDB 이벤트와 outbox 커밋 수락이며 MongoDB 적재 완료 응답이 아니다. 정상 연결에서는 약 1초 주기로 전달한다.

기존 `event_id`, `event_type`, `content_id`, `category`에 `anonymous_id`, `session_id`, `page_path`, `referrer_path`, `query_length`, `filter_name`, `filter_value`를 추가했다. 임의 properties, user_id, occurred_at, 알려지지 않은 필드, query가 포함된 경로는 422다. 콘텐츠 이벤트는 유효한 content_id가 필요하고 page_view는 page_path가 필요하다.

로그인은 선택이지만 토큰을 보냈다면 검증한다. 비로그인은 anonymous_id와 session_id가 필수다. 기존 회원 요청 형식도 유지한다. 찜/결제 등 서버 이벤트와 브라우저 세션을 연결하기 위해 `X-Activity-Anonymous-Id`, `X-Activity-Session-Id`, `X-Activity-Page` 헤더를 사용하며 CORS에도 허용했다. 잘못된 선택 헤더는 분석 문맥에서 제외하고 업무 처리를 실패시키지 않는다.

## 전달, 중복, 장애 처리

1. `Store.event()`가 behavior_events와 event_outbox를 같은 MariaDB 트랜잭션에 기록한다. 찜/결제가 실패하면 이벤트와 대기열도 함께 롤백된다.
2. 두 FastAPI 서버의 lifespan 작업이 1초마다 최대 25개를 처리한다. `FOR UPDATE SKIP LOCKED`로 서로 같은 outbox 행을 동시에 처리하지 않도록 한다. master MariaDB를 사용한다.
3. PyMongo는 `_id=event_id`에 `$setOnInsert` upsert한다. 최초 저장만 인정하고 기존 본문/사용자/ingested_at을 덮어쓰지 않는다. MongoDB ACK 이후에만 SQL delivered_at을 기록한다. Mongo 성공 후 SQL 기록이 실패해도 다음 전달이 안전하다.
4. 실패 시 attempts, 오류 클래스명만 담는 last_error, next_attempt_at을 저장한다. 2초부터 최대 300초까지 backoff하고 계속 재시도한다. DSN/비밀번호/예외 원문은 로그에 남기지 않는다. MongoDB 장애가 정상 MariaDB 업무 저장을 실패시키지 않는다.
5. 브라우저는 네트워크/5xx에 한 번 같은 event_id로 재시도하며 토큰이 바뀌면 이전 이벤트를 새 사용자로 전송하지 않는다. 서버 수락 전 브라우저 종료·오프라인 활동까지 무손실로 보장하지는 않는다.

전송은 at-least-once이며 문서 저장은 event_id 기준 멱등이다. 배포 전의 기존 MariaDB 이벤트를 자동으로 소급 적재하지 않는다. 원본 properties의 `_context`는 전달용 문맥이며 MongoDB에서는 공통 필드로 펼치고 임의 추가 속성을 제외한다.

## 적용 및 확인

실제 URI는 Git 제외 backend/.env에서만 설정한다. 변수 이름/형식은 .env.example 참고. 두 배포 서버에도 MongoDB 설정을 추가했다.

```bash
# backend 폴더에서
python -m pip install -r requirements.txt
python -m alembic upgrade head
python -m app.tasks.setup_events_mongo
python -m app.tasks.events_status
```

Mongo 설정 작업에는 저장소 루트의 database/mongodb/user_events.schema.json이 필요하다. 문서 변경/삭제 없이 validator와 인덱스만 적용한다. 운영 DB의 Alembic 이력이 비어 있어 기존 테이블·컬럼·외래키·인덱스를 ORM과 비교하고 새 outbox 외 차이가 없음을 확인한 후 기존 버전 `65e5c5f31b9a`를 stamp하고 `78a3b1c2d4e5`를 적용했다. 이 baseline 절차를 다른 DB에 검증 없이 반복해서는 안 된다.

브라우저 검증 결과와 MongoDB 조회 방법은 [`database/mongodb/README.md`](../database/mongodb/README.md)에 기록한다.
