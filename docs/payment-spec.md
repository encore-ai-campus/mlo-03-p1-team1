# 모의 결제 명세

## 현재 사용하는 결제 흐름

현재 화면은 사용자 선택·결제 행동 데이터를 수집하는 **모의 결제**를 사용한다. 외부 PG/브라우저 SDK/웹훅/PG 비밀키가 필요하지 않으며 실제 금액 청구·티켓 발권·환불은 발생하지 않는다. 기존 PortOne 경로는 과거 구현 참고용이며 현재 프론트엔드에서 호출하지 않는다.

1. 로그인한 사용자가 상세 화면에서 매수(1–4)를 고르고 모의 결제 확인 창을 연다.
2. 확인 버튼이 `POST /api/v1/payments/simulations`에 `content_id`, `quantity`, UUID `Idempotency-Key` 헤더를 보낸다. 비로그인/만료 세션은 401이다.
3. 서버는 콘텐츠의 등록 가격으로 총액을 계산한다. 요청에 amount/user_id/status 등 다른 필드를 추가하면 422다.
4. 서버는 주문 `PAID`, 결제 이력, 이용 기록 `CONFIRMED`, `payment_completed` 분석 이벤트를 **한 MariaDB 트랜잭션**으로 저장한다. 하나라도 실패하면 모두 롤백한다.
5. 저장에 성공한 서버 응답을 받은 뒤 `/mypage/payments`로 이동한다. 페이지는 `/payments`와 `/reservations`를 결제번호로 합쳐 단일 **결제 내역** 목록을 표시한다. 같은 결제의 이용 기록을 별도 행으로 중복 표시하지 않는다. 콘텐츠명·장소·일정·수량·금액·상태를 한 항목에서 확인하며 새로고침·재로그인 후에도 유지된다.

화면 문구는 ‘결제하기’, ‘결제 완료’, ‘결제 내역’을 사용한다. 내부의 `simulation` 모드와 분석 구분값은 유지하며, 실제 청구가 없다는 안내는 결제 확인 창에서 짧게 제공한다.

## 대상과 기록 구분

- 등록 가격이 0보다 크고 종료되지 않은 콘텐츠가 대상이다. 샘플과 서비스 내 실제 판매 대상이 아닌 콘텐츠도 체험용으로 처리한다. 이미 시작했어도 종료일이 지나지 않았으면 가능하다.
- 무료/가격 미확인 콘텐츠는 금액을 임의 산정하지 않고 모의 결제를 제공하지 않는다. 잔여 좌석/매수 표시는 없다.
- `sim-UUID` payment_id, 결제 이력의 `provider_transaction_id=simulation`, 응답의 `is_simulated=true`로 실제 거래와 구분한다. 기존 테이블을 사용하므로 이번 변경에 DB 마이그레이션은 없다.
- 취소·환불·실제 관람 확인은 이번 범위에 포함하지 않는다. CONFIRMED는 모의 이용 기록 생성 상태이며 실제 예약 또는 관람 완료 증거가 아니다.

## 멱등성과 접근 제어

사용자 행 잠금과 `(user_id, idempotency_key)` 유일 제약으로 동시 재전송에서도 하나의 주문·결제 이력·이용 기록·이벤트만 생성한다. 같은 사용자·요청 키·콘텐츠·수량은 최초 기록을 반환하며, 이후 콘텐츠 가격이 바뀌어도 금액을 다시 계산하지 않는다. 같은 키로 내용이나 결제 방식을 바꾸면 409다. 주문 상세 `GET /payments/{payment_id}`, 결제 목록과 이용 목록은 로그인한 본인만 조회한다. 타인 주문 상세는 404다.

`GET /payments/config`는 `enabled=true`, `mode=simulation`, `refunds_enabled=false`를 반환한다. 모의 결제 활성화는 기존 `PAYMENTS_ENABLED`나 PortOne 환경변수의 영향을 받지 않는다.

## 기존 PortOne V2 명세 (참고용)

아래는 기존 PG 경로에 대한 기록이다. 위 모의 결제 흐름과 활성화 조건을 혼동하지 않는다.

## 구현과 활성화

기본 `PAYMENTS_ENABLED=false`, `REFUNDS_ENABLED=false`. 실제 PG 채널·테스트/운영 키·상품 판매 권한·아래 정책을 팀에서 확정하기 전 활성화하지 않는다. 무료 크레딧 방식은 사용하지 않는다. 샘플 콘텐츠 결제는 설정과 무관하게 금지한다.

프론트는 `@portone/browser-sdk/v2`, 서버는 httpx로 PortOne REST V2를 직접 호출한다. 공식 문서: [인증 결제](https://developers.portone.io/opi/ko/integration/start/v2/checkout), [REST V2](https://developers.portone.io/api/rest-v2/payment?v=v2), [웹훅 서명](https://developers.portone.io/opi/ko/integration/webhook/readme-v2).

## 승인 흐름

1. 인증 사용자가 콘텐츠 ID·수량(1–4)·UUID Idempotency-Key를 서버에 제출한다. 서버가 MariaDB 금액으로 계산하고 `cp-UUID` payment_id를 발급한다.
2. 같은 사용자·키·상품·수량은 같은 주문을 반환한다. 같은 키로 다른 내용이면 409. 생성한 주문의 금액·명칭은 고정된다.
3. 브라우저가 상점/채널, 서버 주문명/금액, KRW, CARD, customData.order_id로 결제창을 요청한다. PG SDK의 성공 응답으로 자체 결제를 승인하지 않는다.
4. 반환값과 모바일 리다이렉트 `/payment/result` 모두 서버 verify를 호출한다. 서버는 `GET /payments/{id}?storeId=...`, `Authorization: PortOne ...`로 재조회한다.
5. payment.id, storeId, customData.order_id, amount.total, currency가 자체 주문과 일치하고 PAID이면 주문/결제 이력/예약을 **단일 MariaDB 트랜잭션**으로 반영한다.

row lock, 주문 키 유일 제약, reservations.payment_id 유일 제약으로 중복 승인/예약을 막는다. API/웹훅의 오래된 응답으로 취소 완료 상태를 결제 완료로 되돌리지 않는다. PG 오류/잘못된 JSON은 502이며 주문은 미확정 상태로 남는다. 사용자는 결제 내역에서 재확인 가능하다.

## 상태와 취소

| 주문 상태 | 의미 | 예약 상태 |
|---|---|---|
| PENDING | 아직 서버가 PAID/취소 상태를 검증하지 않음 | 없음 |
| PAID | 서버 검증 완료 | CONFIRMED |
| CANCELLED | 공급자 전액 취소와 누적 취소액 확인 | 기존 예약 CANCELLED |
| PARTIAL_CANCELLED | 외부에서 부분 취소됨 | 기존 예약 REVIEW_REQUIRED |

공급자 READY/FAILED/기타 중간 상태는 자동 확정하지 않고 PENDING으로 유지한다. 현재 API는 개별 회차·좌석을 판매하지 않으며 예약의 날짜는 콘텐츠 시작일이다. 부분 취소 요청은 제공하지 않는다.

REFUNDS_ENABLED를 켰을 때 구현된 범위는 **콘텐츠 시작일 전(KST) 전액 취소**다. 결제사에 원금과 `currentCancellableAmount`를 함께 전달하고, API 응답 뒤 재조회하여 실제 CANCELLED와 누적 취소액을 확인한다. 타임아웃 뒤에는 먼저 재조회하므로 취소가 완료돼 있었다면 재요청하지 않는다. 동일 주문 동시 취소는 row lock으로 직렬화한다. 일부 PG의 비동기 취소 완료는 후속 웹훅/재확인이 필요하다.

`payment_history`는 상태/취소 누계 변경마다 원금·누적 취소액·공급자 transactionId를 보관한다. 부분 취소를 직접 요청하지 않지만 공급자에서 발생한 부분 취소는 기록하고 수동 확인 대상으로 둔다. 카드·PG 응답 원문은 저장하지 않는다.

## 웹훅

POST `/api/v1/payments/webhook`. PortOne V2 JSON `2024-04-25` 버전. Standard Webhooks 라이브러리로 원문 body와 webhook-id/timestamp/signature를 검증한다(기본 5분 허용). 유효 서명이어도 결제 API로 다시 조회한다. 본문 64KiB 제한. 처리 성공 receipt와 주문 변화는 같은 DB 트랜잭션으로 커밋한다.

같은 webhook-id는 무시. 알려지지 않은 이벤트 종류/미등록 주문은 200으로 무시한다. 잘못된 서명/상점은 400. 외부 장애/DB 실패는 502/503으로 공급자 재전송을 유도한다. 브라우저 verify와 웹훅 중 먼저 도착하는 경로가 상태를 동기화하고 나중 호출은 멱등 처리한다.

## 팀 확정 필요

- 실제 PG, CARD 지원 채널, 테스트→운영 전환 절차와 웹훅 공개 HTTPS 주소.
- 판매 상품 공급 계약, 결제 금액/세금, 단일 일정·회차/방문일 모델, 취소 가능 기한·수수료.
- 부분 환불, 현장 사용 확인, 취소 후 예약 취소/재예약, 비동기 취소 고객 안내 정책.
- 실패/미완료 주문 보존 기간, 정기 대사·운영자 처리 절차와 PG 거래별 환불 상세 회계 기록 범위.

이 구현에서는 위 미확정 범위를 자동으로 가정해 활성화하지 않는다. 실 PG 승인·환불 및 웹훅 수신은 키 설정 뒤 반드시 추가 검증한다. 이번 검증은 문서 기반 로컬 stand-in을 통한 서버 동작 검증이다.
