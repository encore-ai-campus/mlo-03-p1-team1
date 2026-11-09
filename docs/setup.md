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

MariaDB는 VM 두 대로 구성합니다. master는 **192.168.0.161:3306**, slave는 **192.168.0.162:3306**입니다. `DATABASE_URL`은 master, 선택 설정인 `DATABASE_READ_URL`은 SELECT 전용 slave 계정을 사용합니다. 2026-11-06 사용자 요청에 따라 FastAPI 두 대에 콘텐츠 목록·검색·상세와 추천 콘텐츠 조회를 slave로 분리했습니다. 인증·개인 상태·모든 저장·Alembic·수집·outbox는 master를 사용합니다. 읽기 전에 복제 반영을 최대 `DATABASE_REPLICA_WAIT_SECONDS`(기본 0.5초) 기다리고, 지연·연결 장애·조회 오류 시 master로 조회합니다. Master 자체의 자동 장애 전환은 구현하지 않습니다. 연결·권한·운영 검증과 복구는 [읽기 분리 운영 문서](read-replica.md)를 따릅니다. Master → slave 복제는 MariaDB 서버에서 별도로 구성해야 하며, 백엔드 연결 설정만으로 복제가 활성화되지는 않습니다. 현재 서비스 DB 이름은 **`culture`**이며 기존 자료의 `culturepick`은 이전 예시 이름입니다. 실제 계정·암호는 `backend/.env`에서 관리합니다.

DB 관리자에게 `database/mariadb/permissions.sql`의 플레이스홀더를 교체해 실행하도록 요청하세요. 앱은 DML(SELECT/INSERT/UPDATE/DELETE)만, Alembic용 계정은 DDL(CREATE/ALTER/DROP/INDEX 등)까지, 수집 계정은 contents 테이블의 조회/추가/갱신만 필요합니다. `FLUSH PRIVILEGES`는 CREATE USER/GRANT 뒤에 필요하지 않습니다.

`user@host`의 host는 **DB에서 보이는 백엔드의 출발 IP**입니다. 브라우저 IP나 프론트엔드 서버 IP가 아닙니다. 로컬 개발은 로컬 PC의 LAN IP, 분리 배포는 백엔드 서버 IP를 허용합니다. `%` 전체 허용보다 구체적인 IP를 사용하세요. DB 방화벽에도 해당 IP에서 오는 TCP 3306만 허용합니다. DB 서버 bind-address는 내부 통신 인터페이스에 설정합니다.

`backend/.env`의 형식:

```dotenv
DATABASE_URL=mysql+pymysql://<app-user>:<URL-encoded-password>@192.168.0.161:3306/culture?charset=utf8mb4
DATABASE_READ_URL=mysql+pymysql://<reader-user>:<URL-encoded-password>@192.168.0.162:3306/culture?charset=utf8mb4
DATABASE_REPLICA_WAIT_SECONDS=0.5
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

2026-11-06 사용자 요청으로 MongoDB 분석 이벤트 저장을 도입했습니다. 이전 임시 주소 `100.100.100.140` 대신 현재 지정한 MongoDB를 사용하며 실제 URI는 Git 제외 `backend/.env`의 `MONGODB_URL`에 둡니다. `MONGODB_DATABASE=oddinary`, `MONGODB_EVENTS_ENABLED=true`로 설정하고 `alembic upgrade head`, `python -m app.tasks.setup_events_mongo`를 적용한 뒤 FastAPI를 재시작합니다. 실제 상태는 MariaDB가 기준이고 MongoDB 전달은 트랜잭션 outbox로 재시도합니다. 스키마와 검증 결과는 [행동 이벤트 계약](event-contract.md), [MongoDB 안내](../database/mongodb/README.md)를 참고하세요.

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

### 현재 VM 환경의 HTTPS 적용

- 웹 페이지: `https://www.aiready.p-e.kr` → Nginx `192.168.0.151:443`
- 브라우저 API 요청: `https://api.aiready.p-e.kr/api/v1` → HAProxy `192.168.0.155:443`
- HAProxy → 기존 FastAPI 두 대: 현재 HTTP 주소·포트와 분산 설정 유지

`crypto.randomUUID()`는 보안 컨텍스트가 필요하다. HTTP의 사설 IP로 페이지를 열면 상세 화면의 UUID 생성에서 오류가 발생할 수 있으므로 페이지 자체를 HTTPS로 제공해야 한다. API 주소만 HTTPS로 바꾸는 것으로는 해결되지 않는다. HTTPS 페이지에서 호출하는 API도 HTTPS를 사용해야 한다.

프론트엔드 `.env`에는 다음 값을 설정하고 다시 빌드한다. 두 백엔드의 `.env`에는 기존 `CORS_ORIGINS` 배열에 `https://www.aiready.p-e.kr`을 추가하고 프로세스를 재시작한다.

```dotenv
VITE_API_BASE_URL=https://api.aiready.p-e.kr/api/v1
```

#### Nginx 서버

`www.aiready.p-e.kr.zip`을 Nginx 서버의 `/tmp/`에 전송한 다음 실행한다. API 전용 인증서는 www 도메인에 사용할 수 없다.

```bash
sudo install -d -m 700 /etc/nginx/ssl/www.aiready.p-e.kr
sudo unzip /tmp/www.aiready.p-e.kr.zip -d /etc/nginx/ssl/www.aiready.p-e.kr
sudo sh -c 'cat /etc/nginx/ssl/www.aiready.p-e.kr/certificate.crt /etc/nginx/ssl/www.aiready.p-e.kr/ca_bundle.crt > /etc/nginx/ssl/www.aiready.p-e.kr/fullchain.pem'
sudo chmod 600 /etc/nginx/ssl/www.aiready.p-e.kr/private.key
```

`infra/frontend/nginx.conf`의 server 블록을 실제 서비스 설정에 반영한다. 현재 Nginx의 정적 파일 경로는 `/var/www/html`이며 설정에도 이 경로를 사용한다. 다른 환경에서는 실제 정적 파일 경로를 유지한다. 새 `frontend/dist/` 내용을 해당 경로에 배포한 다음 검증·반영한다.

```bash
sudo nginx -t
sudo systemctl reload nginx
```

설정은 443에서 HTTPS를 제공하고 80·3100의 HTTP 요청을 HTTPS로 이동시킨다. Nginx가 컨테이너 안에서 실행된다면 호스트의 443 포트도 컨테이너의 HTTPS 포트로 게시해야 한다.

현재 직접 설치된 Nginx 서버에서는 HTTP 이동 블록을 `/etc/nginx/sites-available/default`, HTTPS 블록을 `/etc/nginx/sites-available/culturepick-https`로 나누어 관리한다. `/etc/nginx/sites-enabled/default`와 `/etc/nginx/sites-enabled/culturepick-https`는 각각 해당 파일의 심볼릭 링크다. 인증서 체인은 `/etc/nginx/ssl/www.aiready.p-e.kr/fullchain.pem`, 개인키는 같은 폴더의 `private.key`이며 개인키 권한은 `600`이다.

#### HAProxy 서버

`api.aiready.p-e.kr.zip`을 HAProxy 서버의 `/tmp/`에 전송한 다음 실행한다.

```bash
sudo install -d -m 700 /etc/haproxy/certs
sudo install -d -m 700 /etc/haproxy/certs/api-source
sudo unzip /tmp/api.aiready.p-e.kr.zip -d /etc/haproxy/certs/api-source
sudo sh -c 'umask 077; cat /etc/haproxy/certs/api-source/certificate.crt /etc/haproxy/certs/api-source/ca_bundle.crt /etc/haproxy/certs/api-source/private.key > /etc/haproxy/certs/api.aiready.p-e.kr.pem'
```

`infra/haproxy/https-bind.cfg.example`의 두 설정 줄을 기존 HTTP frontend 블록 안에 추가한다. 전체 `haproxy.cfg`를 이 조각 파일로 덮어쓰지 않는다. 기존 `bind :80`, `default_backend`, FastAPI 서버 두 대의 주소·포트는 유지한다. frontend와 연결되는 backend는 `mode http`를 사용해야 한다.

```bash
sudo haproxy -c -f /etc/haproxy/haproxy.cfg
sudo systemctl reload haproxy
```

도메인은 브라우저에서 각각 위 Nginx·HAProxy에 도달해야 한다. 공인 주소를 사용하는 DNS 구성이라면 방화벽·NAT에도 각 서버의 TCP 443 연결을 구성한다. DNS A 레코드만으로 포트가 지정되지는 않는다.

서버 반영 후 인증서 검증을 생략하지 않고 다음 요청을 확인한다. `health`는 앱 응답, `ready`는 DB 연결을 확인한다.

```bash
curl -I https://www.aiready.p-e.kr/
curl https://api.aiready.p-e.kr/api/v1/health
curl https://api.aiready.p-e.kr/api/v1/ready
curl -i -X OPTIONS https://api.aiready.p-e.kr/api/v1/contents -H 'Origin: https://www.aiready.p-e.kr' -H 'Access-Control-Request-Method: GET' -H 'Access-Control-Request-Headers: authorization'
```

마지막으로 브라우저에서 HTTPS 도메인으로 상세 화면을 열어 확인한다. 인증서·개인키와 두 `.env`는 Git에 포함하지 않는다.

## 3. 문화포털 API 수집

### 문화공공데이터광장 API 580 — 현재 적재 방식

[문화체육관광부_문화예술공연(통합)](https://www.culture.go.kr/data/openapi/openapiView.do?id=580)은 `https://api.kcisa.kr/openapi/CNV_060/request`를 사용한다. 발급받은 키는 Git 제외 파일 `backend/.env`의 `CULTURE_API_KEY`에 설정한다. DB도 같은 파일의 `DATABASE_URL`을 사용한다. 이 키는 아래의 data.go.kr 기간/상세 API 키와 별개다.

```powershell
# backend 폴더, 가상환경을 활성화한 상태에서 실행
# API 전체 수집 + 사용자 요청에 따른 테스트용 지역·가격 배정 + 적재
python -m app.tasks.import_culture --demo-attributes

# 저장된 원본에서 형식·대상 DB만 확인
python -m app.tasks.import_culture --from-snapshot ../.runtime/culture-kcisa-raw.json --demo-attributes --dry-run

# API를 다시 호출하지 않고 같은 원본으로 재적재
python -m app.tasks.import_culture --from-snapshot ../.runtime/culture-kcisa-raw.json --demo-attributes
```

`--demo-attributes`는 사용자가 요청한 필터 테스트용 지역·관람료를 배정하는 명시적 옵션이다. 적용된 항목은 샘플로 표시하고 실제 판매를 비활성화한다. 이 옵션을 빼면 임의 지역·가격을 배정하지 않는다. 세부 보정 기준은 [데이터 품질](data-quality.md)을 따른다. 원본과 적재 보고서는 `.runtime/`에 저장하며 실제 키·DB 비밀번호를 Git에 포함하지 않는다.

### 기존 data.go.kr 기간/상세 API

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

## 6. 선택: 이전 로컬 DB 다시 시작

기본 백엔드는 위의 VM master를 사용하므로 로컬 DB를 시작할 필요가 없습니다. 이전 로컬 DB가 필요한 경우 프로젝트 루트에서 `powershell -ExecutionPolicy Bypass -File scripts/start-local-db.ps1`을 실행합니다. `.runtime/mariadb`를 재사용하고 127.0.0.1:13306에만 바인딩합니다. 이 DB를 사용하려면 `backend/.env`의 `DATABASE_URL`도 로컬 주소로 변경해야 합니다. 새 PC에서는 `.tools`/`.runtime`가 없으므로 이 보조 스크립트 대신 위의 DB 서버 구성 또는 Docker 절차를 사용하세요. `.runtime/local-db.json`은 로컬 DB 관리용 임의 root 암호를 담은 Git 제외 파일입니다. 외부에 공유하지 마세요.
