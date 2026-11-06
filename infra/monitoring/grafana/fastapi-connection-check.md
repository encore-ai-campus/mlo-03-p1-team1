# FastAPI1 / FastAPI2 연결 재점검

**후속 복구 완료:** 사용자가 수동 서버를 종료한 뒤 요청하여 두 `culturepick-fastapi` 서비스를 시작했다. 두 서버 모두 active/enabled이며 stdout/stderr가 `/var/log/culturepick/fastapi.log`를 가리킨다. 새 테스트 요청은 각 서버의 파일 3건과 Loki 3건씩 일치했고, 대시보드 버전 5에서는 옛 :8000 UNKNOWN 패널을 연결 안내로 교체했다. [복구 검증 결과](fastapi-service-recovery.json). 아래 본문은 복구 전 점검 기록이다.

2026-11-06 20:22 KST부터 실제 두 IP의 API, Prometheus, Grafana, Loki 및 SSH 프로세스 출력을 확인했다. 대시보드는 버전 4 그대로이며 서버/대시보드 설정을 변경하지 않았다. [실측 JSON](fastapi-connection-check.json).

## 결과

| 항목 | FastAPI1 192.168.0.156 | FastAPI2 192.168.0.157 |
| --- | --- | --- |
| `/api/v1/health` | 200, ok | 200, ok |
| `/api/v1/ready` | 200, MariaDB ready | 200, MariaDB ready |
| `/api/v1/contents?size=1` | 200, 정상 콘텐츠 반환 | 200, 정상 콘텐츠 반환 |
| Node Exporter `:9100/metrics` | 200, nodename=fastapi1 | 200, nodename=fastapi2 |
| Prometheus `up{job="node",instance="<IP>:9100"}` | 1 / Grafana UP | 1 / Grafana UP |
| FastAPI `:8000/metrics` | 404 | 404 |
| 새 테스트 요청의 Loki 로그 | 0건 | 0건 |

각 서버에 health/ready/contents 요청을 한 번씩 보냈고, 고유 표식은 `cp-fastapi-link-20261106T112210338Z`다. HTTP 요청 6개는 모두 성공했지만 원본 로그 파일과 Loki에서 표식은 확인되지 않았다. 대시보드 쿼리 30개는 모두 정상 실행되었다. 기존 로그가 조회되거나 쿼리가 성공했다는 사실만으로 최신 로그 수집까지 정상이라고 판단하지 않았다.

## UNKNOWN의 의미

`기존 :8000 수집 UP / DOWN · job=node`(패널 3)는 과거 Node Exporter 대상이 잘못 `:8000`에 등록되었던 문제를 확인하던 진단 패널이다.

```promql
up{job="node",instance=~`(${server:regex}):8000`}
```

현재 Prometheus의 활성 대상에는 두 `:8000 job=node`가 없다. 따라서 빈 시계열을 UNKNOWN / NOT SCRAPED로 표시하는 것이며, FastAPI 다운을 뜻하지 않는다. 현재 OS 수집 상태는 바로 옆 `Node Exporter UP / DOWN · :9100`의 두 UP이 맞다. 이 기존 진단 패널은 제거하거나 ‘과거 수집 대상 없음’ 안내로 바꾸면 혼동을 줄일 수 있다. 값을 억지로 UP으로 바꾸거나 Node Exporter를 :8000에 다시 등록할 필요가 없다.

FastAPI 자체의 가용성은 health/ready 요청으로 별도 확인했고 정상이다. 지속적인 HTTP 가용성 패널이 필요하면 해당 응답을 별도 probe 메트릭으로 수집해야 한다. 아직 FastAPI /metrics가 없어 앱의 요청 카운터·지연 시간 계측은 별도 작업이다.

## 별도로 발견한 최신 로그 수집 중단

두 서버에서 `culturepick-fastapi.service`는 inactive이고 별도의 Uvicorn 프로세스가 동작 중이었다. stdout/stderr는 FastAPI1의 `/dev/pts/2`, FastAPI2의 `/dev/pts/1`을 가리켰다. 현재 요청 로그는 터미널로 출력된다.

Alloy는 active이고 읽는 파일은 계속 `/var/log/culturepick/fastapi.log`다. 활성 파일 수 1, 재시도/드롭 0이지만 실제 앱이 이 파일에 새 요청을 쓰지 않아 테스트 로그가 Loki로 전달되지 않는다. 기존 파일/과거 스트림이 있다는 사실과 최신 수집 상태를 구분해야 한다.

복구 방법은 각 서버에서 현재 수동 Uvicorn을 정상 종료한 뒤 기존에 구성한 서비스를 시작하는 것이다. 이번 점검에서는 사용자의 실행 중 프로세스를 종료하거나 재시작하지 않았다.

```bash
# 먼저 현재 Uvicorn을 실행한 터미널에서 Ctrl+C로 정상 종료한다.
# 동일 포트로 수동 프로세스와 서비스를 동시에 실행하지 않는다.
sudo systemctl start culturepick-fastapi
sudo systemctl status culturepick-fastapi
sudo tail -f /var/log/culturepick/fastapi.log
```

이 서비스에는 기존 실행 명령·작업 디렉터리와 파일 출력 설정이 있다. 두 서버를 한 대씩 전환하고 매번 `/api/v1/ready`가 200인지 확인한 다음, 새 표식 요청의 원본 파일/Loki 로그가 모두 나타나는지 재검증하면 된다. 수동 실행을 계속 사용하려면 동일하게 stdout/stderr를 해당 로그 파일로 기록하는 실행 설정이 필요하다. Alloy가 빈 파일을 읽도록 하거나 OS 로그를 대신 연결하는 것으로는 해결되지 않는다.
