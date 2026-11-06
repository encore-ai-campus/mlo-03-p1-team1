# 사용자 활동 이벤트

저장 위치는 `oddinary.user_events`다. 실제 MongoDB URI와 자격 증명은 Git 제외 `backend/.env`에서 관리한다. 회원/찜/주문/결제/예약은 MariaDB가 기준이고 MongoDB는 분석 이벤트 원본을 저장한다.

- [문서 검증 스키마](user_events.schema.json): 실제 컬렉션에 strict/error로 적용.
- [실제 저장 예시](user_events.examples.json): 브라우저 테스트에서 조회한 이벤트 종류별 문서. BSON Date는 Extended JSON `$date`로 표현.
- [검증 결과](verification-2026-11-06.json): SQL/Mongo 이벤트 ID 대조, 종류별 건수, 전달 완료 및 결제 대조.
- [전체 이벤트 계약](../../docs/event-contract.md): 필드, 생성 주체, 인증, 중복/재시도 정책.

## 브라우저 검증 결과

2026-11-06 `https://www.aiready.p-e.kr`의 실제 UI를 브라우저로 조작했다. 테스트 회원은 `user_id=4`이며, 별도 테스트 계정을 생성해 다른 회원의 찜/결제를 변경하지 않았다. 같은 브라우저에서 비로그인 활동 후 가입했으므로 익명 활동은 user_id=null이고, 이후 활동은 user_id=4다.

테스트 세션은 `a011c3a1-e75a-4f50-a87a-339a1baa37af`다.

| 실제 조작 | MongoDB 이벤트 | 확인 건수 |
| --- | --- | ---: |
| 비로그인 홈 검색, 로그인 후 탐색 검색 | search | 2 |
| 전시 분야 선택 | filter_use | 1 |
| 상세 화면 진입 | content_view | 3 |
| 찜하기 / 찜 해제 | bookmark_add / bookmark_remove | 각 1 |
| 홈·탐색·상세·추천·결제 내역 이동 | page_view | 10 |
| 결제 확인 창 열기 | payment_checkout_open | 1 |
| 결제 확인 버튼 선택 후 완료 내역 조회 | payment_completed | 1 |
| 추천 목록 열기 / 추천 카드 선택 | recommendation_impression / recommendation_click | 24 / 1 |

합계 **45개**. MariaDB behavior_events 45개, MongoDB 문서 45개, 고유 event_id 45개, outbox 전달 완료 45개였다. 누락·추가·중복·대기·전달 오류는 모두 0건이다. 찜 해제 후 MariaDB 찜 상태도 해제인 것을 확인했다.

결제는 기존 화면의 **모의 결제**로만 테스트했다. `content_id=973`, 수량 1, 10,000원, KRW, `payment_mode=simulation`, `payment_id=sim-1441838d-440d-42d8-a50f-c601c190f240`이다. MariaDB 주문 PAID, 결제 이력 1개, 이용 기록 1개와 Mongo 완료 이벤트 1개를 대조했다. 실제 PG 청구·발권·환불을 수행하거나 검증한 결과가 아니다.

검색 원문 ‘전시’, ‘사진’은 저장하지 않고 기존 수집 정책을 유지하여 `query_length=2`만 저장했다. page_path에도 URL query를 제외한다. 현재 전달 주기는 약 1초이며 장애/backoff 구간에는 더 늦을 수 있다.

## MongoDB에서 확인

MongoDB Compass에서 제공된 접속 URI를 사용해 `oddinary` → `user_events`를 선택한다. Filter에는 아래 JSON을 입력한다. 비밀번호나 전체 접속 URI는 조회 결과 파일에 넣지 않았다.

```json
{"session_id":"a011c3a1-e75a-4f50-a87a-339a1baa37af"}
```

Sort는 `{"ingested_at":-1}`로 설정한다. 로그인 후 기록만 보려면 `{"user_id":4}`, 모의 결제 완료는 `{"user_id":4,"event_type":"payment_completed"}`를 사용한다.

mongosh에서도 확인할 수 있다.

```javascript
use oddinary
db.user_events.find({session_id: "a011c3a1-e75a-4f50-a87a-339a1baa37af"})
  .sort({ingested_at: -1})

db.user_events.aggregate([
  {$match: {session_id: "a011c3a1-e75a-4f50-a87a-339a1baa37af"}},
  {$group: {_id: "$event_type", count: {$sum: 1}}},
  {$sort: {_id: 1}}
])
```

## 설정과 운영

두 FastAPI 서버 `192.168.0.156`, `192.168.0.157`에 PyMongo와 변경 코드를 배포하고 같은 MongoDB 설정을 적용했다. 기존 systemd `culturepick-fastapi.service`로 실행하며 두 `/api/v1/ready`가 HTTP 200인 것을 확인했다. 프로세스는 기존과 같은 Python 실행 파일, Uvicorn 인자, 작업 디렉터리를 유지한다. 프론트엔드는 `192.168.0.151:/var/www/html`에 배포했다. 기존 포스터 및 이전 해시 asset은 유지했다.

배포 전 파일과 backend/.env는 각 서버의 `/var/backups/culturepick-events/20261106T103050Z/`에 root 접근 백업을 두었다. 프론트엔드도 같은 경로에 이전 index.html을 보관했다. DB 변경은 기존 업무 테이블 삭제/재생성 없이 Alembic `78a3b1c2d4e5`의 event_outbox 추가만 적용했다. 기존 DB의 비어 있던 Alembic 이력은 ORM 비교 후 이전 버전으로 baseline했다. 상세는 이벤트 계약 참고.

환경변수는 다음 이름을 사용하며 실제 값은 .env에만 둔다.

```dotenv
MONGODB_URL=mongodb://<user>:<url-encoded-password>@<host>:<port>/?authSource=<auth-database>
MONGODB_DATABASE=oddinary
MONGODB_EVENTS_ENABLED=true
```

backend 폴더에서:

```bash
python -m app.tasks.setup_events_mongo
python -m app.tasks.events_status
```

setup 작업은 루트의 `database/mongodb/user_events.schema.json`을 사용해 validator와 인덱스를 적용한다. 두 배포 서버에는 `/home/test/database/mongodb/user_events.schema.json`도 배치했다. 문서를 삭제/수정하거나 샘플 이벤트를 삽입하지 않는다.

Mongo 인덱스는 `_id`, unique event_id, `(user_id,occurred_at)`, `(session_id,occurred_at)`, `(event_type,occurred_at)`, `(content_id,occurred_at)`다. 보존기간은 임의로 정하지 않아 TTL 인덱스가 없다.

SQL 전달 상태도 확인할 수 있다.

```sql
SELECT COUNT(*) AS pending
FROM event_outbox WHERE delivered_at IS NULL;

SELECT event_id, attempts, next_attempt_at, last_error
FROM event_outbox WHERE delivered_at IS NULL
ORDER BY next_attempt_at LIMIT 20;
```

Mongo 장애 시 업무 데이터와 이벤트/outbox는 MariaDB에 커밋되고 전달은 지수 backoff로 재시도한다. 애플리케이션은 Mongo ACK 후에만 delivered_at을 기록한다. 성공 후 SQL ACK 유실은 같은 event_id로 안전하게 재처리한다. 배포 이전의 behavior_events는 자동 backfill하지 않았다.

롤백 시 먼저 `MONGODB_EVENTS_ENABLED=false`로 작업자를 중단하고 앱을 재시작한 뒤 백업 코드/환경변수를 복원한다. 이미 저장된 Mongo 문서와 SQL outbox는 임의 삭제하지 않는다. 이전 프론트 index.html은 보존된 이전 해시 asset을 그대로 참조할 수 있다.

## 자동 검증 범위

- 백엔드 테스트 91개 통과: 기존 서비스/프로필/모의 결제 회귀와 신규 활동 테스트. 테스트는 별도 `culturepick_activity_20261106_test` MariaDB를 사용했다.
- 신규 테스트는 익명 이벤트, 민감/위조 필드 거부, 원본 불변/중복, 커밋 전 비노출과 롤백, 전달 실패/backoff/복구, 두 작업자의 SKIP LOCKED 처리, 찜 업무 실패 시 이벤트 미생성을 검증한다.
- 실제 MongoDB의 별도 `oddinary_activity_test.user_events`에서 upsert 재처리와 validator 거부(오류 코드 121)를 확인했고 생성한 테스트 문서는 정리했다. 운영 oddinary 컬렉션을 테스트 fixture로 지우지 않았다.
- 프론트엔드 테스트 16개 및 TypeScript/Vite 빌드 통과. 실제 브라우저에서 최신 asset을 확인하고 위 활동을 수행했다.
- 이번 경로는 외부 PG HTTP 호출을 사용하지 않는다. 기존 PortOne 경로의 실제 승인/웹훅/환불 연동은 이번 브라우저 검증 범위 밖이다.
