# PortOne V2 결제 명세

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
