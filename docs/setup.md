# 환경 설정과 배포 안내

## 브랜치 전환 후 프론트엔드 import 오류

2026-11-05 확인한 `feature/users` 브랜치는 `App.tsx`·`SurveyDialog.tsx`·`MyPage.tsx`에서 참조하는 필수 소스가 누락되어 있었다. `frontend`에서 이 브랜치로 전환하면 이전 브랜치의 파일은 작업 폴더에서 사라지고, 현재 브랜치의 불완전한 import가 빌드를 막는다. 이는 Vite 캐시나 DB 오류가 아니다.

사용자가 확인한 화면은 직전 `frontend` 브랜치의 `caa5ba1` 버전이다. 이 버전의 프론트엔드 추적 파일 62개를 기준으로 누락·변경된 50개 파일을 원래 경로에 복원했다. `#111216` 배경, Oddinary 화면, Apple 스타일 테마·스프링 인터랙션·화면 전환과 그 참조 파일·기존 테스트를 함께 복원했다. 브랜치 전환이나 파일 이동·삭제는 하지 않았고, `.env`와 다운로드 포스터는 유지했다. 복원 전 파일은 `.runtime/frontend-before-dark-restore-*.zip`에 백업했다.

복구 시에는 사용자가 확인한 디자인 버전의 테마·컴포넌트·참조 파일을 함께 유지한다. 오래된 버전에서 누락 파일 일부만 가져오면 빌드는 통과해도 디자인·동작이 달라질 수 있다. 이 복원은 `npm run build`, 기존 테스트 16개, 실제 브라우저의 배경색·헤더 블러·버튼 스프링 반응·콘텐츠와 포스터 표시로 확인했다.

복원 파일은 해당 파일을 참조하는 코드와 함께 Git 커밋에 포함해야 한다. `git status --short`의 `??`는 아직 추적되지 않은 파일이므로 `git commit -am`만으로는 포함되지 않는다. 공유 전 필수 파일을 명시적으로 `git add`하고 `npm run build`로 누락 여부를 확인한다.

## 로컬 서버 실행

PowerShell 현재 위치를 `CulturePick`으로 두고 두 터미널에서 시작합니다. 루트 `.venv`가 준비되어 있고 루트 `requirements.txt`의 패키지가 설치되어 있어야 합니다.

```powershell
# 터미널 1: 백엔드
.\.venv\Scripts\Activate.ps1
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

```powershell
# 터미널 2: 프론트엔드
npm run dev
```

브라우저 접속 주소는 `http://localhost:5173`, API 문서는 `http://localhost:8000/docs`입니다. 백엔드 코드는 `backend/app`에서 관리하며 서버와 `python -m app.tasks.*` 명령은 `backend` 폴더에서 실행합니다. 프로젝트 루트에서 서버를 실행하려면 `uvicorn --app-dir backend app.main:app --host 0.0.0.0 --port 8000`을 사용하세요. 설정 파일은 `backend/.env`와 `frontend/.env`를 사용합니다. 패키지가 없다면 루트에서 `python -m pip install -r requirements.txt`, `npm --prefix frontend ci`를 각각 한 번 실행합니다. 빌드 화면은 루트에서 `npm run build` 후 `npm run preview`로 실행합니다.

## 수정해야 하는 파일 한눈에 보기

| 파일 | 수정 항목 | 값의 의미 |
|---|---|---|
| `backend/.env` | `DATABASE_URL` | MariaDB 호스트·포트·DB 이름·앱 계정·암호 |
| `backend/.env` | `CORS_ORIGINS` | 브라우저에서 실제 방문하는 프론트엔드 출처 JSON 배열 |
| `frontend/.env` | `VITE_API_BASE_URL` | 브라우저가 직접 접근할 백엔드 주소 + `/api/v1` |
| `backend/.env` | `CULTURE_API_KEY` | 공공데이터포털에서 승인된 문화포털 API 서비스 키 |
| `backend/.env` | `PORTONE_API_SECRET`, `PORTONE_WEBHOOK_SECRET` | PortOne V2 서버 전용 비밀값 |
| `backend/.env` | `PORTONE_STORE_ID`, `PORTONE_CHANNEL_KEY` | 결제 상점·채널 공개 식별값 |
| `frontend/.env` | `VITE_PORTONE_STORE_ID`, `VITE_PORTONE_CHANNEL_KEY` | 선택: 서버가 제공하는 공개 식별값 대신 사용할 값 |
| `backend/.env` | `PAYMENTS_ENABLED`, `REFUNDS_ENABLED` | 팀 정책 및 PG 테스트 완료 후 각각 `true`로 활성화 |
| `database/mariadb/permissions.sql` | DB 이름·계정·암호·허용 IP | 관리자 권한으로 실행할 때 전체 플레이스홀더 교체 |
| `infra/db/.env` | DB 컨테이너 설정 | Docker를 사용하는 DB 서버에서만 설정 |
| `infra/frontend/nginx.conf` | `server_name`, `root`, TLS | 실제 프론트엔드 도메인과 정적 파일 경로 |
| 테스트 실행 환경 | `TEST_DATABASE_URL` | 개발 DB와 분리한 `_test` 접미사의 MariaDB DB |

`.env.example`은 이름과 형식 설명만 담고 있습니다. 복사한 `.env`에 실제 값을 넣고, `.env.example`에 주소·키·비밀번호를 기입하지 마세요. 환경변수는 `.env`보다 우선하며 backend `.env` 경로는 실행 디렉터리와 무관하게 backend 폴더로 고정됩니다.

## 1. MariaDB DB와 계정

임시 DB 서버는 AGENTS.md대로 **100.100.100.130**, 기본 포트 **3306**입니다. 이 환경에서 TCP 연결은 확인했지만 계정 정보가 없어 원격 로그인은 검증하지 않았습니다. 서비스 DB 예시 이름은 `culturepick`입니다. 다른 이름을 쓰면 권한 SQL과 DATABASE_URL의 마지막 경로를 함께 바꾸세요.

DB 관리자에게 `database/mariadb/permissions.sql`의 플레이스홀더를 교체해 실행하도록 요청하세요. 앱은 DML(SELECT/INSERT/UPDATE/DELETE)만, Alembic용 계정은 DDL(CREATE/ALTER/DROP/INDEX 등)까지, 수집 계정은 contents 테이블의 조회/추가/갱신만 필요합니다. `FLUSH PRIVILEGES`는 CREATE USER/GRANT 뒤에 필요하지 않습니다.

`user@host`의 host는 **DB에서 보이는 백엔드의 출발 IP**입니다. 브라우저 IP나 프론트엔드 서버 IP가 아닙니다. 로컬 개발은 로컬 PC의 LAN IP, 분리 배포는 백엔드 서버 IP를 허용합니다. `%` 전체 허용보다 구체적인 IP를 사용하세요. DB 방화벽에도 해당 IP에서 오는 TCP 3306만 허용합니다. DB 서버 bind-address는 내부 통신 인터페이스에 설정합니다.

`backend/.env`의 형식:

```dotenv
DATABASE_URL=mysql+pymysql://culturepick_app:<URL-encoded-password>@100.100.100.130:3306/culturepick?charset=utf8mb4
CORS_ORIGINS=["http://localhost:5173"]
ENVIRONMENT=development
PAYMENTS_ENABLED=false
REFUNDS_ENABLED=false
```

`<URL-encoded-password>`는 실제 암호를 URL 인코딩한 문자열입니다. `@`, `:`, `/`, `#`, `%` 등이 포함되면 `urllib.parse.quote(password, safe='')`로 인코딩해야 합니다. 암호를 명령줄 인수에 직접 넣지 말고 로컬 편집기에서 `.env`를 수정하세요. SQLite URL은 설정 검증에서 거부됩니다.

Alembic은 임시로 마이그레이션 계정의 DATABASE_URL로 실행한 뒤 앱 계정으로 되돌립니다. `.env` 대신 프로세스 환경변수로 주입해도 됩니다. 실제 스키마는 **Alembic만** 적용하고 `schema.sql`을 별도로 실행하지 않습니다.

```powershell
# backend 폴더에서 실행
python -m alembic upgrade head
python -m alembic check
python -m app.tasks.seed # 개발용 가상 콘텐츠만 선택적으로 추가
```

프로필 추가 정보 기능을 업데이트한 환경도 백엔드 실행 전에 `python -m alembic upgrade head`를 적용합니다. `65e5c5f31b9a` 마이그레이션은 기존 회원을 유지하면서 선택 프로필 컬럼과 나이 범위 제약을 추가합니다. 기존 회원의 추가 프로필 항목은 미입력(`NULL`)으로 시작합니다.

DB를 Docker로 실행한다면 DB 서버에서 `infra/db/.env.example`을 `.env`로 복사한 뒤 채우고 `docker compose -f infra/db/compose.yaml up -d`를 실행합니다. compose의 초기 DB/사용자 설정은 **비어 있는 볼륨의 첫 실행에만** 적용됩니다. 기존 DB의 계정·암호는 SQL로 변경하세요. compose가 생성하는 개발용 사용자는 해당 DB 전체 권한을 가지므로 운영에서는 권한 SQL의 앱/마이그레이션 분리를 적용합니다.

MongoDB는 미도입입니다. 따라서 임시 주소 `100.100.100.140`으로 연결하거나 계정을 만들 필요가 없습니다. 추후 합의하면 행동 이벤트 전달·중복·재시도 정책을 먼저 설계합니다.

테스트에는 별도 `culturepick_test` DB와 이 DB에만 DDL/DML 권한이 있는 별도 계정을 생성하고 그 URL을 `TEST_DATABASE_URL`에 지정합니다. pytest가 `_test` 접미사를 확인한 뒤 테스트 테이블의 데이터를 매번 비우므로 공유 데이터가 있는 DB를 사용하지 마세요. 테스트 마이그레이션도 같은 전용 계정으로 실행됩니다.

## 2. 프론트엔드 주소와 CORS

로컬 `frontend/.env`:

```dotenv
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

브라우저가 프론트엔드 Nginx를 경유하지 않고 위 URL을 호출합니다. 배포 시 `localhost`는 방문자 PC를 의미하므로 반드시 **방문자 브라우저가 접근 가능한 백엔드 호스트**로 변경해야 합니다. `VITE_API_BASE_URL`에는 `/api/v1`을 포함합니다.

예를 들어 프론트엔드가 `https://culture.example.com`이고 백엔드가 `https://api.example.com`이면:

```dotenv
# frontend/.env
VITE_API_BASE_URL=https://api.example.com/api/v1

# backend/.env
CORS_ORIGINS=["https://culture.example.com"]
ENVIRONMENT=production
```

CORS 출처에는 경로(`/api/v1`)나 끝 슬래시를 붙이지 않습니다. `localhost`와 `127.0.0.1`은 다른 출처입니다. 두 주소로 방문하면 둘 다 등록하세요. HTTPS 프론트엔드는 HTTPS 백엔드를 호출해야 혼합 콘텐츠 차단을 피합니다. API 비밀값은 `VITE_` 변수에 넣지 않습니다.

Vite 변수는 빌드 시 고정되므로 `.env` 변경 후 **다시 빌드·배포**합니다. Nginx는 SPA 경로를 `index.html`로 돌려주는 설정만 필요하며 API 리버스 프록시는 넣지 않습니다.

## 3. 문화포털 API 수집

[문화포털 사용 가이드](https://www.culture.go.kr/portal/main/contents.do?menuNo=200155)를 따라 공공데이터포털에서 ‘한눈에보는문화정보 조회서비스’를 활용 신청하고 키를 발급받습니다. `CULTURE_API_KEY`에 Decoding 키를 넣는 것을 권장합니다(Encoded 키도 한 번 디코딩 후 httpx가 인코딩).

```powershell
# backend 폴더에서 실행
python -m app.tasks.collect --days 90 --pages 5
# 전용 수집 프로세스로 6시간마다 실행
python -m app.tasks.collect --days 90 --pages 5 --interval 21600
```

단일 수집 프로세스만 실행합니다. 운영에서는 systemd/작업 스케줄러로 재시작을 보장하세요. API 할당량을 고려해 pages를 정합니다. 1페이지 100건이며 상세 조회가 건별 추가됩니다. 수집 실패 시 배치를 롤백하고 이전 데이터는 보존합니다. 실제 호출은 키 발급 뒤 검증해야 합니다.

수집된 콘텐츠는 `bookable=false`입니다. 외부 가격 문자열을 그대로 안내하며 자동으로 내부 판매 금액을 추정하지 않습니다. 실제 티켓 판매는 공급 계약과 날짜·가격·환불 정책을 확정한 콘텐츠만 관리자가 DB를 통해 별도로 등록해야 합니다. 공개 API 수집은 예매 권한을 부여하지 않습니다.

## 4. PortOne V2

백엔드 `.env`에 상점/채널 식별값과 두 비밀값을 넣습니다. `PAYMENTS_ENABLED=true`는 네 값이 모두 있을 때만 실제 활성화됩니다. 프론트의 식별값은 비워두면 `/payments/config`가 반환한 서버 공개 설정을 사용합니다. 프론트에 서버 비밀키는 절대 복사하지 마세요.

PortOne 콘솔에 **백엔드의 공개 HTTPS 주소 + `/api/v1/payments/webhook`** 을 등록하고 V2 `2024-04-25` JSON 웹훅과 해당 환경의 시크릿을 사용합니다. 브라우저 리다이렉트는 프론트엔드 `/payment/result`이며 Nginx SPA fallback이 필요합니다. 테스트 채널과 실연동 채널을 섞지 마세요.

취소 정책은 [결제 명세](payment-spec.md)의 미확정 사항을 팀이 결정해야 합니다. 기본은 `REFUNDS_ENABLED=false`. 실 PG로 서버 금액 검증·정상 결제·중복 웹훅·취소 및 환불액을 검증한 후 운영에 적용하세요. 이번 테스트는 로컬 시뮬레이션입니다.

## 5. 서버 3대 배포

1. DB 서버: MariaDB, 내부 바인딩, 계정·방화벽·정기 백업. 마이그레이션 적용.
2. 백엔드 서버: Python 환경과 `backend/.env`. `backend` 폴더에서 `uvicorn app.main:app --host 0.0.0.0 --port 8000`으로 실행. 브라우저 직접 호출용 TLS/인증서와 공개 DNS는 서버 운영 환경에서 구성. Dockerfile은 앱 실행만 하며 마이그레이션을 자동 수행하지 않습니다.
3. 프론트엔드 서버: 실제 백엔드 주소로 `npm ci && npm run build`한 `frontend/dist/` 내용을 Nginx 정적 경로에 배치. `infra/frontend/nginx.conf`의 root/server_name/TLS를 적용.

기본 예시 root는 `/var/www/culturepick`입니다. 다른 경로에 복사하면 Nginx `root`도 함께 수정합니다. 현재 빌드는 도메인 루트(`/`) 배포를 기준으로 합니다. 하위 경로 배포 시 Vite `base`, BrowserRouter `basename`, 결제 `redirectUrl`, 포스터 경로를 함께 조정해야 합니다.

인증 시도 제한은 프로세스 메모리 기준입니다. 다중 worker/다중 인스턴스 운영 전 공유 limiter를 도입해야 합니다. 세션 토큰은 sessionStorage에 저장되어 탭 단위로 유지되며 자바스크립트 접근이 가능합니다. 외부 스크립트를 최소화하고 CSP·HTTPS를 운영 환경에 적용하세요.

## 6. 이번에 만든 로컬 DB 다시 시작

프로젝트 루트에서 `powershell -ExecutionPolicy Bypass -File scripts/start-local-db.ps1`을 실행합니다. `.runtime/mariadb`를 재사용하고 127.0.0.1:13306에만 바인딩합니다. 새 PC에서는 `.tools`/`.runtime`가 없으므로 이 보조 스크립트 대신 위의 DB 서버 구성 또는 Docker 절차를 사용하세요. `.runtime/local-db.json`은 로컬 DB 관리용 임의 root 암호를 담은 Git 제외 파일입니다. 외부에 공유하지 마세요.
