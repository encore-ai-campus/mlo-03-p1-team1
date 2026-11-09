# MariaDB 읽기 분리 적용 및 검증

2026-11-06, FastAPI `192.168.0.156`, `192.168.0.157`에 직접 반영했다. 기존 master/slave 복제 구성은 유지하고 읽기 연결과 slave 쓰기 제한을 추가했다. DB 스키마 변경은 없다.

| 연결 | 목적 | 계정/제약 |
|---|---|---|
| Master `192.168.0.161:3306/culture` | 모든 저장, 인증, 개인 상태, 트랜잭션, Alembic, 수집, outbox | 기존 `DATABASE_URL` 유지 |
| Slave `192.168.0.162:3306/culture` | 콘텐츠 목록·검색·상세, 추천 콘텐츠 SQL | `culturepick_reader@192.168.0.156` / `@192.168.0.157`, `SELECT ON culture.*`만 허용 |

Slave는 실행 중 `read_only=ON`을 적용했고 `/etc/mysql/mariadb.conf.d/60-culturepick-replica-readonly.cnf`에도 저장했다. DB 재시작은 하지 않았다. 읽기 계정은 slave에만 만들었으며 `%` 접근·쓰기·DDL·관리 권한을 부여하지 않았다. 설정과 권한의 재사용 예시는 [replica 설정](../infra/db/mariadb-replica.cnf.example), [권한 SQL](../database/mariadb/replica-permissions.sql)에 있다. 기존 계정에 예시의 CREATE USER를 재실행하지 않는다.

## 애플리케이션 동작

각 서버의 `/home/test/backend/.env`에 다음 변수를 추가했다. 실제 비밀번호는 서버 `.env`와 Git 제외 운영 파일에만 보관한다.

```dotenv
DATABASE_READ_URL=mysql+pymysql://<reader-user>:<url-encoded-password>@<replica-host>:<port>/<database>?charset=utf8mb4
DATABASE_REPLICA_WAIT_SECONDS=0.5
```

`DATABASE_READ_URL`이 비어 있으면 기존처럼 master만 사용한다. 읽기 엔진과 세션은 쓰기 엔진 `SessionLocal`과 분리하며, 쓰기 코드가 사용하는 `Store.db`는 항상 master다. HTTP 요청·응답 계약은 동일하다.

`GET /api/v1/contents`, `/contents/{id}`, `/recommendations`에서 콘텐츠 조회만 slave로 보낸다. 인증 세션·사용자 정보·찜 여부·평점·개인화 가중치는 master에서 읽는다. 찜·프로필·리뷰·주문·결제·예약·활동 내역 등 나머지 조회 및 모든 변경은 master에 남겨 저장 직후 결과를 확인할 수 있다. 추천/인기순 콘텐츠 SQL에 포함된 찜 집계는 slave에서 실행될 수 있다.

요청에서 master의 `@@GLOBAL.gtid_binlog_pos`를 읽고 slave에서 `MASTER_GTID_WAIT(position, timeout)`이 0을 반환한 뒤 조회한다. 파일/위치 방식으로 동작 중인 기존 복제를 GTID 방식으로 재설정하지 않아도 이 대기를 사용할 수 있다. 기본 0.5초 안에 반영되지 않거나 slave 연결·조회에 SQLAlchemy 오류가 발생하면 해당 콘텐츠 조회를 master에서 재시도한다. Slave 연결 시도 제한은 2초이고 SQL 통신 제한은 대기 시간 올림 + 1초다. 이 구성은 master를 조회하기도 하므로 master 장애를 자동 복구하는 구성은 아니다. `/ready`도 master 상태를 확인한다.

운영 로그는 `Catalog database route=replica endpoint=/api/v1/contents`처럼 연결 경로와 URL 경로만 남긴다. SQL 파라미터·인증 토큰·접속 문자열은 남기지 않는다. 기존 Alloy 수집 대상 `/var/log/culturepick/fastapi.log`에서 확인할 수 있다.

## 실제 검증 결과

| 검사 | 결과 |
|---|---|
| 두 FastAPI 서버의 master 연결 | `server_id=1`, `read_only=0`, DB `culture` |
| 두 서버의 slave 연결 | `server_id=2`, `read_only=1`, 각 서버 IP에 지정한 reader 계정 |
| Reader 권한 | USAGE + `SELECT ON culture.*`만 존재 |
| 각 서버 reader로 INSERT / UPDATE / DELETE 시도 | 모두 MariaDB 1290으로 거부. `WHERE 1=0`의 무변경 쿼리 사용 |
| 각 서버 콘텐츠·추천 API | HTTP 200, 실제 서비스 로그에서 `route=replica` |
| Slave 연결 목록 | `.156`, `.157` 출발 reader 연결을 DB에서 직접 확인 |
| 웹 서비스 로그인·검색·추천 | HTTP 200, 콘텐츠 제목 검색 결과 일치 |
| 테스트 계정 찜 저장 직후 상세/찜 목록 | 즉시 반영 확인, 원래 찜 상태로 복원 |
| Master 저장 → slave 복제 | 테스트 찜 행을 두 DB에서 각각 확인한 뒤 삭제 복원 |
| 복제 상태 | IO Yes / SQL Yes, 지연 0초, IO/SQL 오류 없음 |
| 회귀 및 읽기 분리 통합 테스트 | 전용 MariaDB `_test` DB와 실제 replica 연결 사용, **98 passed** |

통합 테스트는 실제 replica SQL 실행, reader 쓰기 거부, master에 남겨야 할 경로, 연결 실패·GTID 대기 시간 초과·조회 중 오류 시 master 재시도를 검증한다. 추천 후보를 읽은 뒤 후속 replica 조회부터 계속 실패하는 경우에도 이미 읽은 후보를 유지해 HTTP 200과 추천 순서를 보장하는 사례를 포함한다. 장애 테스트는 테스트 프로세스에만 실패를 주입했으며 운영 복제나 DB를 중지하지 않았다. 테스트 DB의 replica 계정은 별도이며 `culture`에 권한이 없다. 운영 DB에 pytest를 실행하지 않는다. `TEST_DATABASE_URL`과 `TEST_DATABASE_READ_URL`은 동일한 전용 `_test` DB의 master와 SELECT 전용 replica URL로 지정한다. 선택 MongoDB 통합 검증은 `RUN_MONGO_TESTS=1`로 실행했다.

## 운영 확인과 복구

두 FastAPI는 `culturepick-fastapi.service`로 정상 실행 중이다. 코드/환경변수 수정 후 각각 `sudo systemctl restart culturepick-fastapi`로 반영한다. `sudo systemctl status culturepick-fastapi`와 `curl -f http://127.0.0.1:8000/api/v1/ready`로 상태를 확인한다. 같은 포트에 수동 Uvicorn을 중복 실행하지 않는다.

Slave의 로컬 DB 관리자 세션에서 다음을 확인한다. 접속 비밀번호를 명령줄 인수에 넣지 않는다.

```sql
SELECT @@server_id, @@read_only;
SHOW SLAVE STATUS\G
SELECT USER, SUBSTRING_INDEX(HOST, ':', 1) AS client_host, DB, COMMAND
FROM information_schema.PROCESSLIST WHERE USER = 'culturepick_reader';
```

두 FastAPI의 변경 전 소스 6개와 `.env`는 각각 `/var/backups/culturepick-read-replica/20261106T123710Z/`에 백업했다. Slave의 변경 전 복제 상태도 같은 경로에 저장했다. 읽기 분리만 해제하려면 두 서버 `.env`의 `DATABASE_READ_URL`을 비우고 각각 서비스를 재시작한다. Slave의 SELECT 계정과 `read_only=ON`은 유지해도 된다.

코드까지 복구하려면 해당 백업의 `app/core/config.py`, `app/db/session.py`, `app/repositories/store.py`, `app/api/deps.py`, `app/api/v1/contents.py`, `app/api/v1/recommendations.py`를 `/home/test/backend/`의 같은 상대 경로에 복원하고 `backend.env`를 `.env`로 복원한 뒤 서비스를 재시작한다. `.env` 권한은 600으로 유지한다. Master의 기존 연결이나 복제 설정을 교체할 필요는 없다.

MariaDB 공식 문서: [GTID 대기 함수](https://mariadb.com/docs/server/reference/sql-functions/secondary-functions/miscellaneous-functions/master_gtid_wait), [읽기 전용 replica](https://mariadb.com/docs/server/ha-and-performance/standard-replication/read-only-replicas). `read_only`는 복제 스레드와 특정 관리자 권한에 예외가 있으므로 애플리케이션 reader에도 SELECT 전용 권한을 별도로 적용했다.

## 2026-11-09 로컬 연결 활성화 및 재검증

로컬 `backend/.env`에는 master용 `DATABASE_URL`만 설정되어 있어 기존 읽기 분리 코드가 비활성 상태였다. `DATABASE_URL`은 유지하고 `DATABASE_READ_URL`에 요청받은 slave 연결을 추가했으며 `DATABASE_REPLICA_WAIT_SECONDS=0.5`로 설정했다. 실제 계정과 암호는 Git에서 제외된 `.env`에만 보관한다. 이번 변경은 로컬 작업 폴더에 적용했으며 배포 서버 설정은 변경하지 않았다.

현재 라우팅은 콘텐츠 목록·검색·상세·추천의 콘텐츠 조회를 slave로 보내고, 회원가입·로그인·리뷰·결제를 포함한 모든 쓰기와 인증·개인 상태 조회는 master에 유지한다. 콘텐츠 응답에 포함되는 최신 평점·본인 찜 여부도 master에서 보강한다. 실행 중인 백엔드는 시작 시 읽은 설정을 사용하므로 `.env` 변경 후 재시작해야 한다.

| 이번 실행에서 확인한 항목 | 결과 |
|---|---|
| 서비스 DB master/slave 연결 | 각각 `server_id=1`, `server_id=2`; slave `read_only=1` |
| 복제 반영 확인 | master의 현재 GTID에 대한 slave `MASTER_GTID_WAIT` 결과 0 |
| 콘텐츠 목록·상세·추천 API | 세 요청 모두 HTTP 200; SQL 이벤트 추적으로 콘텐츠 SELECT가 slave에서 실행됨을 확인 |
| 회원가입·로그인·리뷰 작성·결제·결제 상세·로그아웃 | 전용 `_test` DB에서 성공; 실제 master INSERT 확인 및 slave SQL 실행 0건 |
| 장애 처리 및 회귀 테스트 | 실제 master/slave의 전용 `_test` DB로 pytest 실행, **98 passed, 21 skipped** |

서비스 DB `culture`에는 읽기 검증만 수행했고 쓰기 테스트는 별도 `culturepick_activity_20261106_test` DB에서 수행했다. 선택 외부 HTTP/MongoDB 연동 테스트는 이번 실행에서 제외했다. HTTP API 검증은 FastAPI TestClient로 수행해 별도 테스트 서버나 리스닝 포트를 생성하지 않았다. 테스트 프로세스는 종료했고 DB 엔진 연결을 해제했다. 위 운영 배포 기록의 검증 수치와 이번 로컬 실행의 결과는 별개다.
