# CulturePick - Nginx 연결 검증

**후속 수정 완료:** 사용자의 요청에 따라 Grafana 대시보드 버전 3에 기본 서버 `.151:9100`, 최근 1분 평균 RPS Instant 쿼리, 물리 `sda` 기준 디스크 I/O를 저장했다. URL 변수 없이 다시 열어 기본값을 확인했고 무요청 구간의 RPS는 0으로 표시되었다. 변경 후 [대시보드 JSON](culturepick-nginx.dashboard.json)과 [변경 전 백업](culturepick-nginx.before-fixes.dashboard.json)을 보관했다. 아래 ‘개선할 설정’은 버전 2 점검 당시 발견한 원인과 해결 설명이다.

2026-11-06 20:03 KST부터 실제 웹 서비스와 Grafana에 브라우저로 접속해 확인했다. 결론은 **연결 정상**이다. 다만 대시보드의 기본 서버 선택값과 RPS/디스크 I/O 집계에는 개선할 점이 있다. 서버 설정·대시보드 JSON을 변경하지 않았으며 대시보드 버전 2도 유지되었다. 화면에서만 서버 필터를 선택했다.

[올바른 서버 필터로 대시보드 열기](http://192.168.0.160:3000/d/culturepick-nginx/culturepick-nginx?from=now-1h&to=now&var-log_host=nginx&var-node=192.168.0.151:9100)

기계 판독 결과와 패널별 검증은 [`nginx-connection-check.json`](./nginx-connection-check.json)에 기록했다.

## 실제 연결 상태

| 구간 | 실측 결과 | 판정 |
| --- | --- | --- |
| 브라우저 → Nginx `192.168.0.151` | 탐색 페이지/아이콘 200, 의도적인 없는 정적 파일 요청 404 | 정상 |
| Nginx 서버 → Prometheus `192.168.0.159:9090` | `up{job="node",instance="192.168.0.151:9100"}=1`, 15초 수집 | 정상 |
| Nginx 파일 → Alloy | access.log/error.log 모두 alloy 계정 읽기 가능, 활성 파일 2개 | 정상 |
| Alloy → Loki `192.168.0.158:3101` | 테스트 access 3건/error 1건 확인, 전송 카운터 95→99, 재시도 0 | 정상 |
| Grafana → Prometheus/Loki | 두 데이터 소스 health HTTP 200 / OK | 정상 |
| 대시보드 쿼리 | PromQL 14개 + LogQL 17개 = 31개 모두 HTTP 200 / success | 정상 |

Nginx, Alloy, Node Exporter 서비스는 active였다. 대시보드에서 Node Exporter scrape의 **UP**과 테스트 표식이 포함된 error.log도 직접 확인했다. Prometheus의 네트워크 수신 카운터도 검증 구간에 20,995바이트 증가했지만 다른 통신이 포함될 수 있으므로 요청의 직접적인 대조 기준은 고유 로그 표식이다.

Prometheus는 여기서 Node Exporter를 통해 Nginx 서버의 OS 자원을 수집한다. Nginx가 Prometheus에 직접 push하는 구조는 아니다. 요청 수/RPS/상태 코드 등은 Loki 로그에서 계산한다.

## 브라우저 활동과 로그 대조

고유 표식: `cp-nginx-check-20261106T110327057Z`.

1. `https://www.aiready.p-e.kr/explore?nginx_probe=<표식>`으로 실제 페이지를 열었다.
2. 검색창에서 ‘전시’를 제출하고 검색 결과의 상세 콘텐츠를 열었다.
3. 브라우저에서 `/favicon.svg?nginx_probe=<표식>` 요청으로 200을 확인했다.
4. 브라우저에서 `/assets/<표식>.js`라는 없는 파일을 한 번 요청해 의도적으로 404와 error.log를 만들었다.

고유 표식 기준 access.log 원본 3건과 Loki 3건이 일치했고, error.log 원본 1건과 Loki 1건도 일치했다. access 상태 분포는 **200 두 건, 404 한 건**이다. 최근 15분 대시보드에서 Requests=3, 4xx=1, Error log lines=1, 5xx 오류율=0%를 확인했다. 404/error 1건은 이번 검증에서 만든 테스트 기록이며 실제 서비스 장애가 아니다. 5xx 또는 서버 중단을 유발하는 테스트는 하지 않았다.

실제 수집 라벨:

```logql
{job="nginx", host="nginx", log_type="access"}
{job="nginx", host="nginx", log_type="error"}
```

파일명 라벨은 각각 `/var/log/nginx/access.log`, `/var/log/nginx/error.log`였다. 테스트를 다시 찾으려면 조회 시간을 검증 시각까지 확장하고 아래를 사용한다.

```logql
{job="nginx",host="nginx",log_type="access"}
  |= "cp-nginx-check-20261106T110327057Z"

{job="nginx",host="nginx",log_type="error"}
  |= "cp-nginx-check-20261106T110327057Z"
```

React의 SPA 화면 이동은 HTML을 매번 다시 요청하지 않는다. 검색·상세 API는 브라우저에서 `https://api.aiready.p-e.kr/api/v1/...`로 직접 호출되었고 HTTP 200을 확인했다. 이 API 호출은 프론트 Nginx를 경유하지 않으므로 Nginx access 요청 수와 모든 사용자 클릭/활동 건수가 일치하지 않는 것이 정상이다. 사용자 활동 분석은 MongoDB user_events, API 모니터링은 FastAPI/HAProxy 측 로그와 구분한다.

## 개선할 설정

### 1. 서버 필터의 기본값

대시보드의 `Node Exporter host` 변수 기본값은 `__select_nginx_host__`였다. 실제 Prometheus instance가 아니므로 최초 화면의 OS 지표가 비어 있었다.

즉시 확인 방법:

- `Log host`: **nginx**
- `Node Exporter host`: **192.168.0.151:9100**

두 변수는 독립적이다. 기본값을 바꾸려면 위 값으로 선택한 뒤 대시보드 저장 시 현재 변수 값을 기본값으로 저장한다. 이번에는 선택 후 정상 표시만 확인하고 저장하지 않았다. 다른 FastAPI/DB IP도 선택 목록에 있으므로 Nginx 대시보드에서는 `.151`로 제한하는 편이 혼동을 줄인다.

최근 15분에 실제 요청이 없으면 Loki 패널의 No data도 정상일 수 있다. 테스트 전 실제 최근 로그는 조회 시간 밖에 있었고, 새 요청을 보낸 뒤 정상 표시되었다.

### 2. RPS가 현재값처럼 보이지만 과거 값이 남는 문제

현재 RPS Stat은 `queryType=range`, `[$__auto]`, `lastNotNull` 조합이다. 테스트 트래픽이 끝난 뒤 최신 1분 rate 조회에는 매칭 로그가 없었지만, Stat은 과거 **2 req/s**를 계속 표시했다. 마지막 유효 표본 시각은 `2026-11-06T11:03:44Z`였다. 전체 대시보드에서는 같은 요청 구간을 0.400 req/s로 표시했는데, 패널 크기에 따라 `$__auto` 창이 달라지기 때문이다.

권장 변경:

- 현재 RPS용 Stat의 Query type을 **Instant**로 변경한다.
- 계산 창을 `1m`처럼 고정하고 제목을 ‘최근 1분 평균 RPS’로 명확히 한다.

```logql
sum(rate({job="nginx",host=~"$log_host",log_type="access"}[1m]))
```

무요청 구간에 0을 표시하려면 `or vector(0)`을 붙일 수 있지만, 수집 장애도 0처럼 보일 수 있다. 0 표시만으로 Alloy/Loki 수집 정상 여부를 판단하지 않는다. 이 문제는 연결 장애가 아니라 집계/표시 방식의 문제다. [Loki 쿼리 종류](https://grafana.com/docs/grafana/latest/datasources/loki/query-editor/)

### 3. 디스크 I/O 합산 중복

현재 Disk I/O 패널은 `loop/ram/sr`만 제외하고 모든 장치 rate를 합산한다. 이 서버는 `sda → sda3 → LVM(dm-0) → /` 구조다. 같은 시점의 write rate가 `sda`, `dm-0` 모두 **16,369.628 B/s**로 같았다. 두 계층을 합하면 같은 I/O가 두 번 계산된다.

이 서버의 물리 장치 기준으로 보려면 읽기/쓰기 쿼리를 각각 다음처럼 제한하거나, 장치별 선으로 나누어 표시한다.

```promql
rate(node_disk_read_bytes_total{job="node",instance="$node",device="sda"}[$__rate_interval])
rate(node_disk_written_bytes_total{job="node",instance="$node",device="sda"}[$__rate_interval])
```

## 현재 입력으로는 없는 지표

Prometheus에는 `nginx_*` 메트릭이 없고 `nginx_up`도 빈 결과였다. 현재 패널은 Node Exporter + Loki를 사용하므로 이것이 연결 실패를 뜻하지 않는다. Node Exporter의 UP은 OS 메트릭 수집 성공을 뜻하며 Nginx 프로세스/HTTP 서비스의 가용성 보장은 아니다. [Node Exporter 범위](https://prometheus.io/docs/guides/node-exporter/)

Nginx active/reading/writing/waiting connections가 필요하면 `stub_status`와 Nginx Prometheus Exporter를 별도로 구성해 실제 메트릭을 확인한 뒤 패널을 추가한다. 응답 시간은 현재 combined access 로그에 없으므로 `$request_time` 등을 포함하는 로그 형식과 Alloy/Loki 파싱을 별도로 설계해야 한다. 이번에는 존재하지 않는 메트릭/필드를 만들거나 서버 설정을 바꾸지 않았다. [Nginx stub_status 공식 문서](https://nginx.org/en/docs/http/ngx_http_stub_status_module.html)
