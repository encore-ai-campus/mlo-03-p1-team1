# CulturePick - AGENTS.md

## 1. 프로젝트 개요

CulturePick은 전시·공연·문화행사를 검색하고 사용자 취향 및 활동 데이터를 바탕으로 콘텐츠를 추천하는 서비스다.

외부 공개 API로 문화 콘텐츠를 수집하고, 서비스 내부에서 회원·찜·리뷰·활동 데이터를 관리한다.

## 2. 기술 스택

- **프론트엔드:** React, TypeScript, Vite / 배포 시 Nginx
- **백엔드:** Python, FastAPI, Pydantic, SQLAlchemy, PyMySQL, Uvicorn
- **데이터베이스:** MariaDB / 스키마 변경 관리: Alembic
- **결제 연동:** PortOne V2 (브라우저 SDK + 서버 REST API 및 웹훅)
- **선택 기술:** MongoDB
- **개발 환경:** 로컬 PC 1대에서 프론트엔드·백엔드·DB 통합 개발
- **배포 환경:** 프론트엔드, 백엔드, DB 서버 각 1대 (총 3대)

> SQLAlchemy는 SQLite가 아닌 Python ORM 라이브러리다. 기본 DB는 MariaDB이며 SQLite는 사용하지 않는다.

## 3. 통합 폴더 구조

```text
culturepick/
├── AGENTS.md
├── README.md
├── .gitignore
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── api/
│   │   ├── mocks/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── index.css
│   ├── dist/                   # 빌드 시 자동 생성
│   ├── index.html
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── .env.example            # 필요한 환경변수 이름과 형식만 기록
│   ├── .env                    # 실제 로컬 값 (Git 제외)
│   ├── package.json
│   └── package-lock.json
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── api/
│   │   │   ├── router.py
│   │   │   └── v1/
│   │   │       ├── auth.py
│   │   │       ├── users.py
│   │   │       ├── surveys.py
│   │   │       ├── contents.py
│   │   │       ├── reviews.py
│   │   │       ├── bookmarks.py
│   │   │       ├── recommendations.py
│   │   │       ├── history.py
│   │   │       ├── payments.py      # PG 결제·취소·환불 API
│   │   │       └── reservations.py
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── repositories/
│   │   ├── models/
│   │   ├── collectors/
│   │   ├── pipelines/
│   │   ├── tasks/
│   │   ├── core/
│   │   ├── integrations/       # PortOne 서버 API 연동
│   │   └── db/
│   │       ├── session.py
│   │       ├── base.py
│   │       └── mongo.py           # MongoDB 도입 시
│   ├── alembic/
│   ├── tests/
│   ├── .env.example            # 필요한 환경변수 이름과 형식만 기록
│   ├── .env                    # 실제 로컬 값 (Git 제외)
│   ├── requirements.txt
│   └── Dockerfile
├── database/
│   ├── mariadb/
│   │   ├── schema.sql
│   │   ├── seed.sql
│   │   ├── queries.sql
│   │   ├── indexes.sql
│   │   └── permissions.sql
│   ├── mongodb/               # MongoDB 도입 시
│   ├── analytics/
│   ├── fixtures/
│   ├── backup/
│   └── README.md
├── infra/
│   └── db/
│       ├── compose.yaml
│       ├── mariadb.cnf
│       └── mongod.conf        # MongoDB 도입 시
└── docs/
    ├── requirements.md
    ├── api-spec.md
    ├── erd.md
    ├── data-dictionary.md
    ├── event-contract.md
    ├── payment-spec.md       # PG 결제·환불 흐름 및 상태 정의
    └── data-quality.md
```

## 4. 주요 서비스 기능

- 회원가입·로그인·로그아웃, 초기 취향 설문, 프로필 및 마이페이지
- 문화 콘텐츠 정기 수집, 목록·검색·필터·상세 조회
- 찜하기, 리뷰·평점, 이용 내역, 조회·클릭, 결제 등 활동 이력
- 설문·행동 데이터 기반 추천
- 예약·취소·환불: 팀에서 상세 정책을 확정한 범위에서만 구현
- **결제는 무료 크레딧 방식이 아닌 PortOne V2 결제 연동으로 처리한다.** 결제 요청·서버 검증·결제 내역 조회·취소·환불 기능을 구현한다.
- 잔여 좌석 수·잔여 매수 표시 기능은 구현하지 않는다.

## 5. 공통 개발 규칙

- 기존 파일·폴더의 위치와 이름은 사용자 요청 없이 변경하지 않는다. import 오류는 현재 구조에서 참조 파일·경로와 현재 브랜치의 파일 포함 여부를 확인해 해결한다. 프론트엔드 수정 후에는 빌드를 확인하고 새 필수 소스가 Git 커밋에 누락되지 않도록 확인한다.
- 프론트엔드 디자인 복구 기준은 `frontend` 브랜치의 `caa5ba1` 버전이다. 배경색 `#111216`과 기존 Apple 스타일 테마·인터랙션을 유지하고, 복구 시 테마·컴포넌트·참조 파일을 함께 확인한다. 디자인 변경 없이 오류만 수정하는 작업에서 이전 버전 화면으로 바꾸지 않는다.
- 프론트엔드는 TypeScript(`.ts`, `.tsx`)를 사용한다.
- 백엔드 API 경로는 `/api/v1`을 기본 접두사로 사용한다.
- API 명세는 `docs/api-spec.md`, DB 구조는 `docs/erd.md`에 정리한다.
- FastAPI의 `api/`는 요청 처리, `schemas/`는 데이터 검증, `services/`는 비즈니스 로직, `repositories/`는 DB 접근, `models/`는 ORM 모델을 담당한다.
- `database/`는 테이블·SQL·분석 자료를, `infra/db/`는 DB 서버 실행·설정을, `backend/app/db/`는 애플리케이션의 DB 연결을 담당한다.
- 실제 DB 스키마 변경은 Alembic으로 관리하고 `database/mariadb/schema.sql`은 참고용으로 유지한다.
- `frontend/.env.example`, `backend/.env.example`에는 환경변수 이름과 형식만 기재한다. 실제 주소·키·비밀번호는 각 폴더의 `.env`에 작성하고 `.env`는 Git에 올리지 않는다.
- `frontend/dist/`, `frontend/node_modules/`, `backend/.venv/`는 Git에 올리지 않는다.
- MongoDB 및 추가 인프라는 팀 합의 후 도입한다. 도입한다면 MariaDB는 서비스 상태, MongoDB는 행동 이벤트 기록 용도로 구분한다.

## 6. 로컬 실행과 서버 배포

- 프론트엔드는 Vite 빌드 결과물이 `frontend/dist/`에 생성되며, 배포 시 Nginx가 해당 정적 파일을 제공한다.
- 백엔드는 `backend/.env`의 `DATABASE_URL`로 MariaDB에 연결하고, DB 구조 변경은 Alembic으로 적용한다.
- 배포 시 프론트엔드, 백엔드, DB를 각각 별도 서버에 실행한다.
- mariadb 서버는 100.100.100.130, mongodb 서버는 100.100.100.140으로 임시로 설정하고 테스트한다.

### 통신 흐름 (리버스 프록시 사용 안 함)

- **브라우저 → 프론트엔드(Nginx):** React 정적 파일을 직접 요청한다.
- **브라우저 → 백엔드(FastAPI):** React가 백엔드 주소로 API를 **직접 호출**한다. 프론트엔드 Nginx를 경유하지 않는다.
- **백엔드(FastAPI) → DB(MariaDB):** DB 서버에 직접 연결한다.
- **브라우저 ↔ PortOne 결제창:** 프론트엔드가 PortOne 브라우저 SDK로 결제를 요청한다.
- **백엔드(FastAPI) ↔ PortOne 서버:** 결제 조회·검증·취소·환불을 처리하고 PortOne 웹훅을 수신한다.
- 프론트엔드와 백엔드의 출처(origin)가 다르므로 FastAPI의 CORS 허용 출처에 **실제 프론트엔드 주소**를 등록한다.

## 7. MariaDB / MongoDB 저장 데이터 구분 (팀 공통 기준)

MongoDB 도입 시 두 DB는 다음 역할을 구분한다. **MongoDB 미도입 상태에서는 사용자 행동 이벤트도 MariaDB에 저장할 수 있다.**

| 저장소                | 저장할 데이터                         | 예시                                                                     |
| ------------------ | ------------------------------- | ---------------------------------------------------------------------- |
| **MariaDB**        | 서비스에서 현재 상태와 정확한 거래 기록이 중요한 데이터 | 회원·인증, 초기 설문, 문화 콘텐츠, 찜 상태, 리뷰·평점, 예약·이용 내역, 주문, 결제 승인 상태, 결제·취소·환불 이력 |
| **MongoDB (도입 시)** | 추천·분석용 사용자 행동 이벤트 원본            | 콘텐츠 조회, 검색, 필터 사용, 추천 노출·클릭, 찜/찜 취소 행동 이벤트, 리뷰 화면 방문 등                 |

- **찜·리뷰·예약 등의 실제 상태는 MariaDB가 기준 데이터(Single Source of Truth)다.** MongoDB의 이벤트는 이 상태를 대체하지 않는다.
- **이용 내역(예약·관람 상태)은 MariaDB**, 조회·클릭 등의 \*\*행동 로그는 MongoDB(도입 시)\*\*로 구분한다.
- 행동 이벤트에는 최소한 `event_id`, `event_type`, `user_id`(로그인한 경우), `content_id`(해당하는 경우), `occurred_at`을 정의하고, 필요한 부가 정보만 추가한다.
- 이벤트 이름, 필드 형식, 중복 처리 기준은 `docs/event-contract.md`에 정한다.
- MariaDB와 MongoDB 간 이벤트 전달이 필요한 경우 중복 저장·누락·재시도 처리를 설계한다. 업무 데이터 저장 실패 시 이벤트만 성공한 상태를 정상 처리하지 않는다.
- MongoDB에는 카드번호, 결제 인증 정보, PG 비밀키, 사용자 비밀번호 등 민감 정보를 저장하지 않는다.

## 8. PortOne V2 결제 연동 기준

- 외부 결제 연동 플랫폼 **PortOne V2**를 사용한다. PortOne에서 연결할 실제 PG 채널과 결제수단은 팀에서 확정한다.
- 프론트엔드는 PortOne 브라우저 SDK(`@portone/browser-sdk/v2`)로 결제창을 호출하고 결과 화면을 표시한다. 결제 관련 화면과 API 호출 코드는 기존 `frontend/src/pages/`, `frontend/src/api/` 아래에서 관리한다.
- 백엔드는 주문 생성·결제 상태 검증·취소·환불을 처리한다. 결제 엔드포인트는 `backend/app/api/v1/payments.py`, 로직은 `services/`, DB 처리는 `repositories/`, PortOne API 통신은 `integrations/`에 구현한다.
- **결제 처리 절차:** 백엔드에서 주문 및 고유 `paymentId` 발급 → 브라우저에서 PortOne 결제 요청 → 백엔드에 `paymentId` 전달 → 백엔드가 PortOne REST API로 결제 상태·금액·주문 대응 관계 확인 → MariaDB 주문·결제 상태 반영.
- **브라우저의 성공 응답만으로 결제 완료 처리하지 않는다.** 서버가 자체 주문 정보와 PortOne 결제 조회 결과를 검증해야 한다. 웹훅도 서명 등을 검증하고 필요 시 PortOne API로 재조회한다.
- 주문·결제·취소·환불 정보와 실제 예약 상태의 기준 저장소는 **MariaDB**다. MongoDB에는 결제 페이지 조회 등 분석 이벤트만 저장하며, 카드 정보·PortOne 비밀키 등 민감 정보를 기록하지 않는다.
- PortOne 결제 요청·웹훅 수신·취소 및 환불에서 중복 요청이 발생해도 중복 처리되지 않도록 `paymentId`와 거래 상태를 기준으로 **멱등성**을 보장한다.
- `frontend/.env.example`에는 `VITE_API_BASE_URL`, `VITE_PORTONE_STORE_ID`, `VITE_PORTONE_CHANNEL_KEY` 등의 **이름과 형식만** 작성한다. 실제 공개 가능한 상점·채널 식별값은 `frontend/.env`에 입력한다.
- `backend/.env.example`에는 `DATABASE_URL`, `PORTONE_API_SECRET`, `PORTONE_WEBHOOK_SECRET` 등 **이름과 형식만** 작성한다. 실제 비밀값은 `backend/.env`에서만 관리하며 프론트엔드의 `VITE_` 변수에 넣지 않는다.
- 테스트/운영 채널, 결제 금액 산정, 주문·예약 연결, 결제 상태, 부분/전체 취소·환불 정책과 웹훅 엔드포인트는 `docs/payment-spec.md`에서 확정한다.
