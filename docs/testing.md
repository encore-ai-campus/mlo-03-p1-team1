# 검증 기록

## 결제 내역 통합 화면 검증 (2026-11-05)

`npm run build`와 프론트엔드 테스트 16개가 통과했다. 결제번호별 중복 제거, 주문 금액·상태 우선, 이용 내역 없는 대기 주문 유지, 주문 조회 범위 밖 이용 기록 유지, 부분 취소 금액 보존을 검증했다. 결제 화면 문구를 일반 결제 용어로 정리했으며 이 변경에서는 개발 서버를 실행하지 않았다.

## 모의 결제 추가 검증 (2026-11-05)

- `python -m pytest backend/tests -m 'not upstream' -q`: 전용 MariaDB `_test` DB에서 57개 통과. 기존 외부 PG/수집 stand-in 대상 20개는 이번 실행에서 제외했다.
- 모의 결제는 비로그인/만료 인증 거부, 서버 금액 산정, 샘플·진행 중 콘텐츠 허용, 타인 이력 분리, 재로그인 후 이력 유지, 잘못된 입력·요청 키 거부, 동시 재전송 단일 생성, DB/이벤트 기록 실패 시 전체 롤백을 검증했다. PG 어댑터 초기화를 실패시키는 검사에서도 모의 결제가 통과했다.
- `npm run build` 통과, `npm --prefix frontend test` 11개 통과.
- Postman collection lint: 7개 요청, 오류/경고 0. 실제 로컬 FastAPI/MariaDB 대상 collection run: 7개 요청 / 15개 assertions 통과. `--report-events=false`로 로컬 실행했다. 설치된 CLI 1.73.0은 `postman status` 명령을 지원하지 않는다.
- Chrome에서 비로그인 결제 버튼→로그인 안내→테스트 회원가입→샘플 2매 모의 결제→`/mypage/payments` 자동 이동→이용·결제 목록에 각각 36,000원 표시→새로고침 후 유지 확인. 콘솔 오류/경고 없고 PG 요청 없음을 확인했다.
- 브라우저 테스트로 생성한 계정과 해당 계정의 모의 결제·이벤트는 검증 후 정리했다. 기존 사용자 데이터는 변경하지 않았다.

아래 기록은 모의 결제 추가 전 기존 기능의 검증 이력이다.

## 프로필·마이페이지 확장 검증 (2026-11-04)

- 실제 로컬 MariaDB의 전용 `_test` DB에서 `python -m pytest -c backend/pytest.ini -q -m 'not upstream'`: **39 passed, 20 deselected**. 이번 범위의 외부 PortOne·문화포털 호출은 수행하지 않았다.
- 선택 프로필 초기값, 정규화·영속 저장·재로그인 조회, 부분 수정 시 나머지 항목 유지, 선택 항목 삭제, 만 나이 경계값, 잘못된 입력의 원자적 거부, 본인 인증·회원 간 분리, 설문 수정 시 프로필 유지 검증.
- 로컬 개발 DB에 `alembic upgrade head` 적용 및 `alembic check` 통과. OpenAPI·참고 SQL 재생성 완료. 원격 DB 변경 없음.
- `npm run build` 통과.
- 브라우저에서 가입 직후 초기 설문 표시, 미완료 설문을 닫은 뒤 재로그인 시 자동 표시 없음, 나의 정보 기본 표시, 다섯 프로필 항목과 이름 수정 후 조회 반영 확인.
- 마이페이지의 다섯 메뉴 경로 이동, 취향 수정 저장 후 프로필 유지, 새로고침 시 저장 정보와 세션 복원 확인. 390×844 및 320×740 모바일에서 세로 메뉴 유지·가로 넘침 없음. 최종 브라우저 콘솔 error/warn 없음.

## 초기 통합 검증 (2026-11-03)

검증일: 2026-11-03. Python 3.14.8 / Node 24.22.0 / MariaDB 11.4.5(프로젝트 내부 포터블 테스트 인스턴스) / Postman CLI 1.73.0. SQLite 사용 없음.

## 자동 검사

| 검사 | 결과 | 증명하는 범위 |
|---|---|---|
| `RUN_UPSTREAM_TESTS=1 python -m pytest -q` | **34 passed**, exit 0 | 실제 MariaDB + 실제 FastAPI + 로컬 외부 HTTP stand-in |
| `alembic upgrade head`, `alembic check` | 적용 성공, 차이 없음 | 개발·테스트 DB 마이그레이션, ORM 스키마 일치 |
| `npm run build` | TypeScript·Vite 빌드 성공 | 배포 정적 산출물 생성 |
| `postman collection lint postman/collections/culturepick` | 0 errors, 0 warnings | 저장한 v3 요청 구조 |
| `postman collection run ... --report-events=false` | 5 requests / **10 assertions passed**, exit 0 | 실행 중 FastAPI의 health/ready/목록/401/422 계약 |
| OpenAPI·참고 SQL 생성 | 성공 | docs/openapi.json, database/mariadb/schema.sql 재현 가능 |

pytest의 유일한 경고는 설치된 Starlette가 TestClient의 httpx 사용에 대해 출력한 upstream deprecation이다. 테스트 실패는 없다. 테스트 대상 DB는 `_test` 이름 검사 후 별도로 초기화하며 개발 DB 데이터는 사용하지 않는다.

기능 테스트는 인증/만료/로그아웃 폐기/가입 중복, 검색·지역·무료·종료 제외·날짜·페이징, 사용자별 찜 분리와 멱등성, 리뷰 갱신/평점/삭제, UUID 행동 이벤트 중복, 설문·조회에 따른 추천 순위 변화를 검증한다.

외부 연동 테스트는 서버 금액 계산, 동일 요청 키와 동시 주문 3개 요청의 단일 주문, 동시 검증 3개 요청의 단일 예약, 금액·통화·상점·주문 위변조 거부, 타인 주문 접근 차단, PG HTML 500/비JSON 200 시 미확정 유지, 서명 웹훅 중복·위조·오래된 시각 거부, 정책 미활성 환불 차단, 전액·동시 취소의 단일 PG 취소, 취소 누계 기록, 취소 완료 상태 회귀 차단을 확인한다.

문화포털 stand-in으로 실제 HTTP 목록/상세·키 오류·XML 정규화와 2회 수집 upsert·공급자 장애 시 기존 데이터 보존을 확인했다. simulation 출력에 GET /payments, POST /payments/{id}/cancel, GET /period, GET /detail 경로의 실제 요청 이벤트가 기록된 것을 확인했다.

## Chrome DevTools 브라우저

사용자가 지정한 Chrome DevTools 도구만 사용해 직접 제어했다. 빌드 결과를 `http://localhost:5173`에서 Vite preview로 제공하고 브라우저가 `http://localhost:8000/api/v1`에 직접 접근했다.

- 홈·목록·포스터 표시, 회원가입, 자동 취향 설문, 음악/재즈 저장.
- 추천 페이지 첫 항목 ‘밤의 재즈, 서울’ 및 재즈 추천 이유 확인.
- 재즈 검색 제출 후 결과 1개 확인.
- 상세 찜 저장 후 찜 목록과 최근 조회에 같은 콘텐츠가 나오는지 확인.
- 4점 리뷰 작성 후 본문과 평점 4.0/리뷰 1개 반영 확인.
- 마이페이지 로그아웃 후 로그인 안내 전환, 재로그인 성공 후 다시 로그아웃.
- 390×844, 320×740 모바일 에뮬레이션과 데스크톱 표시 확인. 문서 가로 넘침 없음. 키보드 포커스·네이티브 모달·감소된 모션 스타일 제공.
- 최종 페이지에서 Chrome 콘솔 error/warn 없음.

## 확인하지 않은 범위

- 원격 `100.100.100.130:3306`: TCP 연결만 성공. 계정 미제공으로 원격 인증·스키마·권한 미검증.
- 실제 PortOne PG 승인·취소·모바일 결제창·실제 공급자 웹훅 전달. 테스트 채널 키와 공개 HTTPS 수신 URL 필요.
- 실제 문화포털 서비스 키 인증/실제 데이터 수집. 서비스 활용 승인과 키 필요.
- Nginx/TLS의 3대 서버 실배포, 실제 방화벽·복구/백업·부하 검증.

Postman 로그인/공유 workspace가 없으므로 공급자 소유 mock 탐색은 생략했고 공식 문서를 토대로 로컬 stand-in을 작성했다. Orbit 공개 API 탐색은 403으로 실패하여 공식 PortOne/문화포털 문서를 사용했다. 클라우드 배포나 공개 mock 생성은 하지 않았다.

이 에이전트 환경에서는 Vite dev의 esbuild 의존성 최적화가 상위 디렉터리 파일 접근 제한으로 실패한다. 배포 빌드와 preview는 성공했으며 브라우저 검증은 해당 빌드로 수행했다. 실행/재현 명령은 README 및 setup.md를 참조한다.
