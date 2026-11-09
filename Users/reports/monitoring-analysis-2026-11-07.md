# Oddinary Playwright 부하 및 데이터 적재 모니터링 분석

- 수집 확인 시각: 2026-11-07 08:30 UTC (17:30 KST)
- 서비스: `https://www.aiready.p-e.kr/`
- 분석 실행: 2026-11-07 06:36:52–07:37:29 UTC (약 60분)
- 부하 전 기준 구간: 06:21:52–06:36:52 UTC (15분)
- 부하 후 관측 구간: 07:37:29–08:30:12 UTC (약 53분)
- 스케줄러 설정상 사용자 100명, 최대 동시 활동 5명. 실행 종료 후 2시간 휴식 중인 시점의 부분 관측이며 휴식 종료 시점까지의 전체 추이는 포함하지 않는다.

## 요약

Loki에서 Playwright 호스트(`[IP_REDACTED]`, HeadlessChrome UA)의 Nginx access log 5,936건이 부하 구간에 확인됐고, 모두 HTTP 200이었다. 같은 구간의 FastAPI access log는 19,205건(평균 5.28 RPS)이었으며, fastapi1과 fastapi2는 각각 9,602건과 9,603건으로 사실상 50:50 분배였다. FastAPI 로그상 4xx/5xx는 0건이었다.

Prometheus에서 확인한 CPU는 부하 구간 동안 애플리케이션 서버에서는 평균 약 3.4%, 데이터베이스 서버에서는 평균 약 3.2–4.3%였지만, DB 서버 CPU는 짧은 피크가 관측됐다. 메모리 사용률은 크게 변하지 않았다. 측정된 것은 호스트 시스템 자원 지표이며, MongoDB/MariaDB의 실제 쿼리·쓰기 지표는 수집되지 않았다.

실제 MongoDB DB/컬렉션 이름, 문서, 활동별 필드 및 문서 수 차이는 이 조사에서 검증하지 못했다. 현재 연결 가능한 모니터링에는 MongoDB exporter가 없고, 읽기 전용 MongoDB 접속 URI/계정도 제공되지 않았다. 따라서 데이터 적재 성공이나 누락 여부를 결론낼 수 없다.

## 1. 요청 및 서버 자원

### Nginx / FastAPI 요청

| 구간 | Nginx: Playwright 출발지 요청 | Nginx 평균 RPS | FastAPI 요청 | FastAPI 평균 RPS | FastAPI 오류(4xx/5xx) |
|---|---:|---:|---:|---:|---:|
| 실행 전 15분 | 0 | 0.00 | 966 | 1.07 | 2 (401 1건, 404 1건) |
| 실행 중 약 60분 | 5,936 | 1.63 | 19,205 | 5.28 | 0 |
| 실행 후 첫 53분 | 0 | 0.00 | 3,201 | 1.01 | 0 |

Nginx 요청 집계는 access log에서 클라이언트 IP `[IP_REDACTED]`를 필터링했다. 부하 구간의 해당 요청은 모두 200이었다. 집계에는 문서, JS/CSS 및 포스터 이미지 요청이 포함돼 API 요청량과 숫자가 다르다. 실행 전·후의 0은 해당 Playwright 호스트에서 온 요청이 없었다는 뜻이며, 사이트 전체 트래픽이 0이었다는 의미는 아니다.

FastAPI는 access log에 기록된 HTTP 요청을 집계했다. 부하 구간 상위 경로는 `/api/v1/history/events` 9,428건, `/api/v1/health` 3,628건, `/api/v1/contents` 2,086건, `/api/v1/payments/config` 745건, `/api/v1/recommendations` 639건이다. 기록상 예약·결제·찜·리뷰 경로 요청도 있었으나, 요청 로그만으로 데이터베이스 반영 성공을 증명할 수는 없다.

FastAPI access log에는 프록시 주소 `[IP_REDACTED]`가 클라이언트로 기록돼 원래 Playwright IP를 기준으로 API 로그만 분리할 수 없다. 기준 및 실행 후 구간에는 헬스체크 요청이 각각 898건과 3,154건 포함되어 있어 운영 헬스체크를 포함한 전체 서버 access log 집계다. FastAPI RPS는 따라서 Playwright 전용 수치가 아니다.

### FastAPI 분배

| 구간 | fastapi1 (`[IP_REDACTED]`) | fastapi2 (`[IP_REDACTED]`) | 비율 |
|---|---:|---:|---:|
| 실행 전 | 484 | 482 | 50.10% / 49.90% |
| 실행 중 | 9,602 | 9,603 | 49.997% / 50.003% |
| 실행 후 첫 53분 | 1,600 | 1,601 | 49.98% / 50.02% |

로그에 남은 요청 수는 균등하게 분배됐다. 이는 FastAPI 호스트 로그 기준의 관측이며, HAProxy의 자체 요청·재시도·대기열 지표를 확인한 것은 아니다. Grafana/Prometheus 설정에서 HAProxy exporter 또는 HAProxy 메트릭 타깃은 발견되지 않았다. `[IP_REDACTED]`는 FastAPI 로그의 peer 주소일 뿐, 이 주소의 HAProxy 역할과 내부 분배 지표는 현재 모니터링에서 직접 검증되지 않았다.

### CPU 및 메모리

Prometheus node exporter의 1분 단위 표본을 집계했다. CPU 값은 부하 구간의 평균 / p95 / 최대, 메모리는 같은 구간의 평균 / p95 / 최대 사용률(%)이다. CPU는 5분 rate 기반이라 구간 경계 주변 표본이 인접 구간과 겹칠 수 있다.

| 호스트 | 역할 | CPU 실행 전 평균 | CPU 실행 중 평균 / p95 / 최대 | CPU 실행 후 평균 | 메모리 실행 전 평균 | 메모리 실행 중 평균 / p95 / 최대 | 메모리 실행 후 평균 |
|---|---|---:|---:|---:|---:|---:|---:|
| [IP_REDACTED] | Nginx | 0.80% | 1.38 / 1.73 / 1.78% | 0.87% | 27.25% | 26.73 / 27.25 / 27.43% | 27.43% |
| [IP_REDACTED] | FastAPI 1 | 2.21% | 3.45 / 3.91 / 4.01% | 2.14% | 20.38% | 22.71 / 23.50 / 23.73% | 23.39% |
| [IP_REDACTED] | FastAPI 2 | 2.03% | 3.41 / 4.03 / 4.25% | 2.09% | 21.71% | 22.98 / 23.88 / 23.92% | 23.54% |
| [IP_REDACTED] | MariaDB master | 1.51% | 4.29 / 15.83 / 19.28% | 2.12% | 24.89% | 24.45 / 24.81 / 25.25% | 24.30% |
| [IP_REDACTED] | MariaDB slave | 1.12% | 3.16 / 14.03 / 17.60% | 1.43% | 19.32% | 19.27 / 19.98 / 19.99% | 19.53% |
| [IP_REDACTED] | MongoDB | 2.25% | 4.25 / 15.00 / 19.14% | 2.79% | 17.72% | 17.21 / 17.82 / 17.85% | 17.95% |

관측된 호스트 CPU/메모리는 실행 후 부분 구간에서 낮은 수준으로 돌아오는 양상을 보였다. 단, 실행 후 2시간 중 첫 53분만 수집했으며 이후 회복은 이 결과로 확인하지 않았다. MariaDB 2대와 MongoDB의 CPU 최대치는 순간 피크다. 현재 데이터만으로 해당 피크를 특정 쿼리나 쓰기 작업에 귀속할 수 없다.

## 2. API 응답시간, 오류 및 부하 분산

- HTTP 상태 코드는 FastAPI access log에서 확인했다. 실행 중 관측된 19,205건은 200 9,731건, 201 146건, 202 9,328건이며 4xx/5xx는 0건이다.
- FastAPI의 응답 지연 분포(p50/p95/p99)는 로그에 요청 처리시간이 없고 Prometheus에 애플리케이션 메트릭이 없어 확인할 수 없다.
- 요청/초와 API 경로별 건수는 로그에서 산출했다. 사용자 원 IP가 proxy 뒤에서 보존되지 않아 Playwright 요청만 분리한 API RPS는 확인 불가다.
- fastapi1/2의 로그 건수는 실행 중 거의 정확히 절반씩 분산됐다. HAProxy 자체 exporter/통계 페이지가 수집 타깃에 없어 backend 상태, 큐, 재시도, 연결 수와 HAProxy 레벨 지연은 미확인이다.

## 3. MongoDB 적재 상태

### 확인된 내용

- Grafana 데이터베이스 대시보드에는 MongoDB 로그와 `[IP_REDACTED]`의 Node Exporter CPU/메모리/네트워크/디스크 지표가 있다.
- Loki에서 `job=mongodb`, `host=mongodb` 로그가 확인되고, 표본 로그는 WiredTiger checkpoint 메시지였다.
- Prometheus active targets에는 MongoDB exporter가 없다. 수집된 메트릭 이름에도 `mongodb_*` 계열이 없었다.
- Grafana/MongoDB 모니터링 설정에서 CRUD 작업별 이벤트, 저장 지연, 쓰기 오류, 문서 수 지표를 확인하지 못했다.

### 확인할 수 없는 내용

읽기 전용 MongoDB 접속 URI/계정이 없으므로 실제 DB명, 컬렉션명, BSON 문서 구조/필드/값, 실행 전후 문서 수, 행동별 저장 여부 및 사용자별 누락 여부를 직접 조회하지 않았다. 실제 문서 예시는 확보하지 못했으므로 보고서에 예시를 만들어 넣지 않았다. 실행 로그의 HTTP 202/201도 DB 저장 결과나 영속성을 보증하지 않는다.

MongoDB 적재 검증을 완료하려면 읽기 권한의 MongoDB 접속 정보와 실행 전후 스냅샷 조회가 필요하다. 쓰기량/오류/지연 시계열을 위해서는 MongoDB exporter를 배포하고 Prometheus scrape target을 추가해야 한다. 이 변경은 이번 조사에서는 하지 않았다.

## 4. MariaDB 상태

Grafana는 master `[IP_REDACTED]`과 slave `[IP_REDACTED]`의 로그 및 Node Exporter 자원을 수집한다. 두 서버 모두 CPU/메모리 표본은 위 표에 정리했다. Prometheus 타깃에는 MariaDB/MySQL exporter가 없고, `mysql_*` 계열 지표도 없었다. 따라서 연결 수, 쿼리/초, slow query, 쿼리 지연, 복제 지연은 확인할 수 없다. 실행 중 DB 호스트 CPU의 순간 상승은 관측됐지만, 실제 쿼리 부하량이나 원인으로 환산할 수 없다.

## 5. 기존 및 추가 Grafana 대시보드

기존 대시보드는 유지했다.

- `CulturePick - Nginx`: Loki access/error 로그와 Nginx Node Exporter 시스템 지표
- `CulturePick · FastAPI1 / FastAPI2`: FastAPI 로그. 요청률/건수/오류율/응답시간 영역은 대시보드 설명상 수집 대기 상태
- `CulturePick - Databases`: MariaDB/MongoDB 로그와 호스트 시스템 지표

현재 확보된 지표를 한 화면에서 보도록 `CulturePick - Monitoring Overview` 대시보드를 추가했다. CPU/메모리 그래프와 Nginx, FastAPI, DB 로그 패널만 포함하며, 존재하지 않는 메트릭을 만들어 표시하지 않는다. Prometheus와 Loki 기존 데이터소스를 사용한다. 기존 3개 대시보드 JSON은 수정 전에 [`grafana-backup-2026-11-07`](./grafana-backup-2026-11-07/)에 백업했다. 대시보드 payload도 [`grafana-ops-overview-payload.json`](./grafana-ops-overview-payload.json)에 보관했다.

추가 대시보드 URL: [CulturePick 운영 요약](http://[IP_REDACTED]:3000/d/culturepick-ops-overview/culturepick-efbfbd)

대시보드 시간 범위를 2026-11-07 06:21:52 UTC 전부터 08:30:12 UTC까지 설정하면 실행 전·실행 중·실행 후 부분 구간을 비교할 수 있다. 2시간 휴식 전체 비교는 휴식 종료 후 데이터를 더 수집해야 한다.

## 6. 수집 현황 및 필요한 설정

| 항목 | 현재 수집 | 현재 확인 가능 | 필요한 추가 설정 |
|---|---|---|---|
| Nginx 요청/상태/경로 | Loki access log | 출발지 필터 건수, 상태 코드, 경로, 구간별 평균 RPS | 요청 처리시간이 필요하면 Nginx log format에 `$request_time`을 기록하고 수집 |
| 호스트 CPU/메모리 | Prometheus Node Exporter | 6개 호스트의 사용률 추이 | 추가 없음 |
| FastAPI 요청/상태/경로 | Loki FastAPI access log | 구간별 요청 수/RPS, 경로/상태, 서버별 분배 | 원 IP 전달/로그 포함, Prometheus 앱 메트릭 미들웨어 또는 OpenTelemetry 계측 |
| FastAPI 지연 | 없음 | 확인 불가 | 요청 duration histogram을 노출하고 Prometheus scrape 설정 추가 |
| HAProxy | exporter/로그 타깃 없음 | FastAPI backend 로그 분배만 간접 비교 | HAProxy Exporter/Stats endpoint와 Prometheus target 설정 |
| MongoDB CRUD/쓰기 | mongod 로그 일부, Node Exporter | 호스트 자원과 일반 로그 | MongoDB exporter + Prometheus target, DB read-only 계정으로 스키마/문서 대조 |
| MariaDB 쿼리/연결 | DB 로그 일부, Node Exporter | 호스트 자원과 일반 로그 | mysqld_exporter를 각 인스턴스에 구성하고 Prometheus target 설정 |

Exporter/애플리케이션 계측은 아직 설치하거나 설정하지 않았다. 이번 조사에서는 기존 Prometheus 설정이나 서비스 설정을 변경하지 않았다.

## 7. 결론 및 후속 확인

- 확인된 정상 신호: 실행 중 Nginx access 요청 5,936건 모두 200, FastAPI access log의 실행 중 4xx/5xx 0건, 두 FastAPI 서버 간 로그 요청 수 50:50, 호스트 메모리 사용률 안정.
- 관측된 부하 변화: FastAPI 평균 로그 RPS는 실행 전 1.07에서 실행 중 5.28로 증가했다. Nginx Playwright 호스트 요청은 실행 중에만 관측됐다. DB 호스트는 CPU 순간 피크가 있었으나 높은 지속 사용률은 관측되지 않았다.
- 검증 불가: API 지연시간, HAProxy 내부 지표, MongoDB 실제 문서/컬렉션/쓰기/오류/지연, MariaDB 연결/쿼리/지연, 사용자별 데이터 누락 여부.
- 다음 단계: 읽기 전용 MongoDB 계정으로 실제 문서와 전후 count를 조회하고, MongoDB/MariaDB/HAProxy 및 FastAPI latency exporter·계측을 추가한 뒤, 휴식 종료까지의 Prometheus/Loki 구간을 포함해 동일 분석을 갱신한다.

## 집계 근거

Prometheus API active targets와 range query, Grafana API의 기존 대시보드 및 데이터소스 정의, Loki query_range의 실행 전·중·후 access log를 사용했다. Loki 로그는 60초 단위 구간으로 나눠 조회했고, HTTP 메서드/경로/상태 코드를 실제 로그 행에서 집계했다. Prometheus 표본은 1분 간격이다. 보고서의 평균 RPS는 각 구간의 총 로그 건수를 구간 초로 나눈 값이며, 별도 로그 누락/중복 검증용 계측은 없다.
