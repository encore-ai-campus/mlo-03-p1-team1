# CulturePick FastAPI 서버 모니터링

Grafana Import용 파일은 [`culturepick-fastapi.dashboard.json`](./culturepick-fastapi.dashboard.json)이다. 현재 수집 상태를 그대로 반영하므로, Import만으로 모든 패널에 데이터가 나타나지는 않는다. 확인되지 않은 FastAPI 메트릭이나 Loki 라벨을 실제 수집 데이터처럼 사용하지 않았다.

**2026-11-06 후속 수정 완료:** 두 FastAPI 서버의 실제 요청 로그를 `/var/log/culturepick/fastapi.log`에 기록하도록 구성하고 Alloy → Loki 수집 및 Grafana 로그 패널을 연결했다. [실제 대시보드](http://192.168.0.160:3000/d/culturepick-fastapi-servers), [로그 패널](http://192.168.0.160:3000/d/culturepick-fastapi-servers?viewPanel=15&from=now-15m&to=now).

**서비스 실행 복구:** 수동 Uvicorn 실행으로 파일 로그 수집이 중단된 문제를 확인한 뒤, 사용자가 수동 프로세스를 종료한 상태에서 두 `culturepick-fastapi` 서비스를 시작했다. active/enabled 및 서버별 새 요청 로그를 재검증했다. 옛 `:8000 job=node` UNKNOWN 진단 패널은 API/시스템 포트 안내로 교체하여 대시보드 버전 5에 저장했고 생성기에도 반영했다. 현재 활성 쿼리 검증은 PromQL 24개 + LogQL 3개 = 27개다. [복구 기록](fastapi-service-recovery.json).

## 파일

| 파일 | 용도 |
| --- | --- |
| `culturepick-fastapi.dashboard.json` | Import 가능한 Classic Dashboard JSON, 15개 패널 |
| `discovery.json` | 생성 당시 HTTP 응답 상태, 수집 대상, 메트릭 확인 결과, 쿼리 검증 결과 |
| `generate_dashboard.py` | 실제 수집 데이터를 다시 조회하여 JSON 생성 및 쿼리 검증. Python 표준 라이브러리만 사용 |
| `server-config/` | 실제 적용한 systemd 서비스, logrotate, 서버별 Alloy 설정 사본 |
| `grafana-dashboard.before-log-fix.json` | 로그 연결 전 Grafana 대시보드 및 메타데이터 백업 |

최초 JSON 생성 때는 원격 설정을 변경하지 않았다. 이후 사용자의 로그 수정 요청에 따라 두 서버의 실행·로그 설정과 Grafana의 설명/로그 패널(ID 1, 14, 15)을 변경했다. 브라우저 검증 중 단일 IP의 정규식 이스케이프 문제가 확인되어 Node/로그 쿼리의 서버 선택자도 raw string 인용으로 수정했다. 백엔드 소스, 의존성, Prometheus 설정, Grafana 데이터 소스는 변경하지 않았다. 계정 비밀번호는 결과물에 저장하지 않았다.

## 최초 점검 기록 — 후속 수정 전

2026-11-06 약 17:52~18:00 KST에 HTTP API와 SSH로 확인했다. 정확한 HTTP 재조회 시각은 `discovery.json`의 `observed_at_utc`에 기록되어 있다. 아래 내용과 대시보드 상단 설명은 **생성 시점의 기록**이며 실시간 상태 판정은 쿼리 패널에서 확인한다.

| 항목 | FastAPI1 `192.168.0.156` | FastAPI2 `192.168.0.157` |
| --- | --- | --- |
| `/api/v1/health` | HTTP 200, `status=ok` | HTTP 200, `status=ok` |
| `:9100/metrics` | Node Exporter HTTP 200 | Node Exporter HTTP 200 |
| `:8000/metrics` | HTTP 404 | HTTP 404 |
| Prometheus 수집 대상 | `job=node`, `instance=192.168.0.156:8000`, DOWN | `job=node`, `instance=192.168.0.157:8000`, DOWN |
| Prometheus의 해당 서버 Node 데이터 | 없음 | 없음 |
| Alloy 프로세스 | active | active |
| Alloy 파일 대상 | `/var/log/app.log`, 파일 없음 | `/var/log/app.log`, 파일 없음 |
| Alloy 활성 파일 / 전송 로그 수 | 0 / 0 | 0 / 0 |

최초 점검 당시 Prometheus `http://192.168.0.159:9090`에서 확인된 Node 시계열의 `instance`는 `localhost:9100`이었다. 두 FastAPI 서버의 데이터로 간주하지 않았다. 당시 활성 수집 대상은 잘못 지정된 두 `:8000`과 Prometheus 자체였다. **후속 점검에서는 두 서버의 `:9100` 대상이 이미 UP으로 변경되어 실제 Node 데이터가 조회되었다. 이 로그 수정 작업에서 Prometheus 설정은 변경하지 않았다.**

최초 점검 당시 Loki `http://192.168.0.158:3101`의 최근 7일 라벨 및 FastAPI 스트림 조회 결과는 비어 있었다. 초기 `/ready`는 HTTP 503과 `Pattern Ingester not ready`를 반환했고, 이후 HTTP 200 `ready`를 반환했다. 로그 복구 후에는 두 서버의 실제 스트림이 조회된다.

Grafana `http://192.168.0.160:3000/api/health`는 HTTP 200, 버전 `13.3.0`이었다. Prometheus는 `2.45.3+ds`, Loki는 `3.7.9`였다.

## 패널과 필터

- 서버 필터: FastAPI1, FastAPI2, 복수 선택, All. 시계열은 서버별로 분리하여 비교한다.
- Node Exporter 상태: `up{job="node",instance="<IP>:9100"}`. 후속 점검에서 두 서버 모두 UP을 확인했다.
- FastAPI 연결 안내: 삭제된 `:8000 job=node`를 상태 조회하지 않고 API :8000과 시스템 수집 :9100의 구분을 설명한다. 실시간 API 상태 측정값은 아니다.
- CPU, 메모리, 파일시스템별 디스크 사용률, 장치별 디스크 읽기/쓰기, 인터페이스별 네트워크 수신/송신.
- 요청 수, RPS, 응답 시간, HTTP 오류율: 현재는 **수집 대기 안내 패널**이다. 존재하지 않는 요청 메트릭을 사용하는 활성 쿼리는 없다.
- 로그: Loki에서 실제 확인한 `job=fastapi`, `host=fastapi1/fastapi2`, `filename=/var/log/culturepick/fastapi.log` 스트림을 조회한다. 서버별/전체 선택과 문자열 검색을 지원한다.

`up=0`은 **Prometheus가 해당 대상의 메트릭을 수집하지 못했다**는 의미다. 이번처럼 FastAPI는 정상인데 `/metrics`만 404여도 DOWN이다. 시계열이 없는 상태는 DOWN 또는 0%로 보정하지 않는다. FastAPI 자체의 지속적인 HTTP 가용성 판정은 `/api/v1/health`에 대한 별도 헬스체크 수집이 필요하다. 현재는 해당 메트릭이 없어 만들지 않았다.

사용한 Node 메트릭은 다음과 같다. 이름은 Prometheus와 두 Exporter에서 확인했고, `job`, `instance`는 Prometheus에서, `cpu`, `mode`, `device`, `fstype`, `mountpoint`는 실제 시계열 및 Exporter 응답에서 확인했다. 최신 `discovery.json`에는 두 서버 `:9100`의 실제 결과를 기록했다.

```text
node_cpu_seconds_total
node_memory_MemAvailable_bytes
node_memory_MemTotal_bytes
node_filesystem_avail_bytes
node_filesystem_size_bytes
node_disk_read_bytes_total
node_disk_written_bytes_total
node_network_receive_bytes_total
node_network_transmit_bytes_total
```

CPU는 idle 비율을 제외한 사용률, 메모리는 MemAvailable 기준, 디스크 공간은 avail/size 기준이다. 네트워크는 B/s로 표시하며 링크 속도 대비 백분율이 아니다. 디스크 I/O는 장치별로 표시하고 `dm-0`과 `sda`를 합산하지 않는다.

## 수집 설정과 후속 수정 결과

### 1. Prometheus Node Exporter 대상 수정

최초 점검 시 필요했던 조치다. 후속 점검에서 이미 두 `:9100` 대상이 UP인 것을 확인했으므로 현재 설정을 다시 교체할 필요는 없다. 아래는 대상 형식에 대한 참고다.

`192.168.0.159`의 `/etc/prometheus/prometheus.yml`에 있는 기존 `job_name: node`의 대상을 다음처럼 **교체**해야 한다. 전체 설정 파일을 이 내용으로 덮어쓰거나 같은 이름의 job을 중복 추가하지 않는다.

```yaml
scrape_configs:
  # 기존 prometheus job 및 기타 설정은 유지
  - job_name: node
    static_configs:
      - targets:
          - '192.168.0.156:9100'
          - '192.168.0.157:9100'
```

운영자가 변경한 뒤 `promtool check config /etc/prometheus/prometheus.yml`로 검증하고 Prometheus 설정을 reload한다. [Prometheus 수집 설정 문서](https://prometheus.io/docs/prometheus/latest/configuration/configuration/)

두 대상이 `/targets`에서 UP이고 다음 쿼리에 서버별 결과가 나타나는지 확인한다. 수정 전에는 빈 결과가 맞다.

```promql
up{job="node",instance=~"192[.]168[.]0[.](156|157):9100"}
node_memory_MemTotal_bytes{job="node",instance=~"192[.]168[.]0[.](156|157):9100"}
```

기존 JSON의 CPU·메모리·디스크·네트워크 패널은 이 수정만으로 데이터를 표시할 수 있다. 기존 `:8000 job=node` 진단 패널이 이후 NO DATA가 되는 것은 정상이다. 생성 당시 설명을 갱신하려면 JSON을 재생성한다.

### 2. FastAPI 요청 계측

프로젝트의 `backend/app/main.py`와 `backend/requirements.txt`에는 Prometheus 요청 계측이 없고 실제 서버 `/metrics`도 404였다. Node Exporter는 요청 수·HTTP 상태 코드·응답 시간을 제공하지 않는다.

팀에서 계측 방식을 정해야 한다. 한 가지 선택지는 `prometheus-fastapi-instrumentator`이며, 아래는 **추후 별도 변경을 위한 예시**다. 이번 작업에서는 설치하거나 코드를 수정하지 않았다. 라이브러리 버전 및 다중 워커 운용 방식은 도입 시 확인한다. [Instrumentator 공식 저장소](https://github.com/trallnag/prometheus-fastapi-instrumentator)

```python
# 추후 backend 의존성에 prometheus-fastapi-instrumentator를 추가한 경우
from prometheus_fastapi_instrumentator import Instrumentator

# FastAPI app 생성 후 등록하는 예시
Instrumentator(
    should_group_status_codes=False,
    excluded_handlers=["/metrics"],
).instrument(app).expose(app, include_in_schema=False)
```

두 서버에 계측을 적용하여 `/metrics`가 HTTP 200을 반환한 뒤 Prometheus에 **별도의** FastAPI job을 추가한다.

```yaml
  - job_name: fastapi
    metrics_path: /metrics
    static_configs:
      - targets:
          - '192.168.0.156:8000'
          - '192.168.0.157:8000'
```

두 서버의 실제 API에 요청을 보내고, 최소 몇 차례의 scrape가 끝난 뒤 생성 스크립트를 다시 실행한다. Node Exporter가 아닌 FastAPI 앱이 요청 메트릭을 제공해야 한다.

생성기는 위 계측기의 기본 스키마 중 **Prometheus에 실제 나타난 이름과 라벨만** 활성화한다.

| 패널 | 재생성 시 확인하는 실제 수집 데이터 |
| --- | --- |
| 선택 기간 요청 수 / RPS | `http_requests_total`, `job`, `instance`, `status` |
| 평균 응답 시간 | 같은 job의 `http_request_duration_seconds_sum`, `http_request_duration_seconds_count` |
| p95 응답 시간 | `http_request_duration_highr_seconds_bucket` 또는 `http_request_duration_seconds_bucket`, `le=+Inf` 포함 |
| HTTP 오류율 | 요청 카운터의 실제 `status` 라벨. 4xx / 5xx를 분리 |

이 표의 FastAPI 메트릭은 **현재 수집되지 않는다**. 다른 계측기나 라벨을 선택한다면 생성기의 스키마 인식 부분을 실제 응답에 맞춰 조정해야 한다. 예를 들어 `status_code`를 `status`라고 가정하지 않는다. 요청이 없는 구간은 오류율을 0%로 단정하지 않으며, 요청이 있지만 오류 상태의 시계열만 없는 경우에만 0%로 표시한다. p95는 histogram이 없으면 표시하지 않는다.

### 3. Alloy 로그 파일 경로·권한 및 Loki 수집 복구 — 적용 완료

두 서버의 `/etc/alloy/config.alloy`에서 다음 설정을 적용하고 Loki의 실제 스트림에서도 확인했다.

```text
__path__ = /var/log/culturepick/fastapi.log
job      = fastapi
service  = mlops-api
host     = fastapi1 또는 fastapi2
env      = production
push URL = http://192.168.0.158:3101/loki/api/v1/push
tail_from_end = true
```

`job`, `service`, `host`, `env`는 원래 설정을 유지했다. Loki가 추가한 `service_name=mlops-api`, `detected_level=info`도 실제 응답에서 확인했다.

`/var/log/app.log`는 두 서버 모두 없었다. 실행 중인 Uvicorn stdout/stderr는 각각 터미널(`/dev/pts/2`, `/dev/pts/1`)을 가리켰다. `/home/test/culturepick-uvicorn-20261106T060643Z.log`, `/home/test/culturepick-uvicorn-20261106T060714Z.log`도 있었으나 권한이 600이고 현재 stdout 대상이 아니므로, 이 파일을 활성 로그로 단정하여 연결하지 않았다.

사진에 있는 로그의 용도는 아래와 같다. FastAPI의 현재 요청 로그를 OS 로그로 대체하지 않았다.

| 경로 | 내용 / 판단 |
| --- | --- |
| `/var/log/syslog` | OS 및 서비스 로그. 기존 Uvicorn 요청 로그는 없었음 |
| `/var/log/auth.log` | 로그인·sudo 등 인증 로그 |
| `/var/log/kern.log`, `dmesg` | 커널·장치 로그 |
| `/var/log/journal/` | systemd journal 저장소. 기존 터미널 실행 Uvicorn 출력은 기록되지 않았음 |
| `/var/log/culturepick/fastapi.log` | 이번에 연결한 실제 FastAPI 요청·오류·기동/종료 로그 |

두 서버에 적용한 내용:

1. 기존 프로세스의 사용자(root), Python 실행 파일, Uvicorn 인자, 작업 디렉터리를 확인하고 그대로 `culturepick-fastapi.service`에 반영했다. 한 서버씩 기존 프로세스를 SIGTERM으로 정상 종료하고 서비스를 시작하여 헬스체크를 통과한 뒤 다음 서버를 변경했다.
2. systemd `StandardOutput/StandardError=append:/var/log/culturepick/fastapi.log`로 출력을 지속적으로 기록한다. 서비스는 부팅 시 시작되도록 enable했다. 앞으로 터미널에서 같은 포트로 Uvicorn을 중복 실행하지 않는다. [systemd 출력 설정](https://www.freedesktop.org/software/systemd/man/255/systemd.exec.html)
3. 디렉터리는 `root:alloy 0750`, 파일은 `root:alloy 0640`으로 구성하고 `sudo -u alloy test -r`로 읽기 권한을 검증했다.
4. `/etc/logrotate.d/culturepick-fastapi`에 일 단위, `maxsize 10M`, 7개 보관, 압축, `copytruncate` 회전을 추가했다. 회전은 logrotate 스케줄에 따라 수행되며 10MB의 엄격한 실시간 상한은 아니다. `copytruncate`의 복사·잘라내기 사이에 극소량의 로그가 유실될 수 있다.
5. 기존 Alloy 설정은 경로 한 곳만 교체했다. `alloy validate`, `systemd-analyze verify`, `logrotate --debug`를 통과한 뒤 Alloy를 reload했다.
6. 새 API 요청을 보내 실제 파일 증가, 활성 파일 수 1, Loki 전송 건수 증가, 두 host의 실로그를 확인했다. Grafana 브라우저에서도 로그 패널과 서버 필터를 검증했다. `tail_from_end=true`는 유지했다. [Alloy 파일 수집 문서](https://grafana.com/docs/alloy/latest/reference/components/loki/loki.source.file/)

서버에서 확인할 때:

```bash
sudo systemctl status culturepick-fastapi alloy
sudo tail -f /var/log/culturepick/fastapi.log
sudo -u alloy test -r /var/log/culturepick/fastapi.log
```

Loki 실제 스트림 확인:

```bash
curl -G 'http://192.168.0.158:3101/loki/api/v1/series' \
  --data-urlencode 'match[]={job="fastapi",host=~"fastapi1|fastapi2"}'
```

추가로 Loki 설정의 HTTP 포트는 `3101`인데 `pattern_ingester.metric_aggregation.loki_address`는 `localhost:3100`이었다. 해당 기능을 사용할 계획이면 실제 리스닝 포트와 맞는지 점검해야 한다. 초기 readiness 503의 원인이라고 확정하지는 않는다. [Loki 설정 문서](https://grafana.com/docs/loki/latest/configure/)

JSON을 재생성하여 실제 스트림으로 로그 쿼리를 활성화했다. IP 서버 필터를 공유하기 위해 LogQL의 `label_format`에서 `host`를 IP에 대응시키는 임시 `server_ip` 라벨을 만든다. 이는 Loki에 원래 저장된 라벨로 주장하는 값이 아니다. 로그 검색어는 문자열 포함 검색이며 빈 검색어도 동작하도록 `${search:doublequote}`로 인용한다. [LogQL 문서](https://grafana.com/docs/loki/latest/query/log_queries/), [Grafana 변수 형식](https://grafana.com/docs/grafana/latest/visualizations/dashboards/variables/variable-syntax/)

두 서버의 원래 Alloy 설정과 이전 프로세스 명령은 `/var/backups/culturepick-monitoring/20261106T094715Z/`에 보관했다. 롤백이 필요하다면 신규 서비스를 stop/disable하고, 백업의 `config.alloy`를 복원하여 Alloy를 reload한다. 그 후 백업의 `previous-process.json`에 기록된 명령을 `/home/test/backend`에서 원래 사용자(root)로 실행한다. 서비스와 수동 프로세스를 동시에 실행하지 않는다. 기존 backend 소스와 `.env`는 변경하지 않았다.

## Grafana 적용

1. `http://192.168.0.160:3000`에 로그인한다.
2. Connections → Data sources에서 Prometheus URL을 `http://192.168.0.159:9090`, Loki URL을 `http://192.168.0.158:3101`로 설정하고 Save & test한다. 이미 등록되어 있다면 해당 데이터 소스를 사용한다.
3. Dashboards → New → Import에서 `culturepick-fastapi.dashboard.json`을 업로드한다.
4. Import 화면의 Prometheus / Loki 항목에 해당 데이터 소스를 연결하고 Import한다. JSON에 특정 데이터 소스 UID를 고정하지 않았다.
5. 서버 필터에서 FastAPI1, FastAPI2 또는 All을 선택한다. 두 서버를 선택하면 각각의 선이 표시된다. 기본 조회는 최근 1시간, 갱신은 30초다.

후속 수정에서 원격 Grafana의 기존 대시보드를 브라우저로 갱신했다. 현재 Node 자원과 로그는 실데이터를 표시하며 FastAPI 요청 메트릭은 수집 대기다. 기존 `:8000 job=node` 진단은 대상 삭제로 NO DATA가 정상이다. 새 환경에서 적용할 때는 위 Import 절차를 사용한다. [Grafana Import 안내](https://grafana.com/docs/grafana/latest/visualizations/dashboards/build-dashboards/import-dashboards/)

## 수집 복구 후 재생성 및 검증

프로젝트 루트에서 실행한다. 원격 요청은 GET뿐이며 서버 설정을 바꾸지 않는다. 출력 파일은 이 폴더의 JSON 두 개이고, 기존 생성 파일을 갱신하므로 수동 편집 사항은 미리 보관한다.

```powershell
python infra/monitoring/grafana/generate_dashboard.py
```

실제 수집 상태를 다시 탐색하고, 확인된 메트릭·라벨로만 API 및 로그 패널을 활성화한다. 새 JSON을 동일 UID로 다시 Import하여 대시보드를 갱신한다. 생성기는 현재의 고정 IP와 Node `job=node`, FastAPI `instance=<IP>:8000` 형식을 대상으로 한다. 수집 라벨을 바꾸면 생성기도 맞춰야 한다.

파일 변경 없이 기존 JSON 쿼리만 재검증하려면 다음을 실행한다.

```powershell
python infra/monitoring/grafana/generate_dashboard.py --validate-only
```

최초 생성 시 PromQL 27개를 검증했고, 로그 복구 후 재생성에서는 FastAPI1 / FastAPI2 / All의 **PromQL 27개 + LogQL 3개 = 30개 쿼리**가 HTTP 200 / success였다. 단일 선택 시 Grafana가 실제 만드는 `192\.168\.0\.156` 형식으로도 검증했다. 패널 ID·그리드 겹침·JSON 구조도 검증한다. FastAPI 요청 메트릭은 아직 없어 해당 네 패널은 수집 대기를 유지한다. 브라우저 검증은 서버별 필터와 빈 검색어/GET 검색어의 실제 로그 표시를 포함한다.
