"""Discover live data and build an importable dashboard. Remote operations are GET only.

Uses the Python standard library. Never reads SSH passwords or changes a server.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen


HERE = Path(__file__).resolve().parent
SERVERS = {"192.168.0.156": "fastapi1", "192.168.0.157": "fastapi2"}
PROM_DS = {"type": "prometheus", "uid": "${DS_PROMETHEUS}"}
LOKI_DS = {"type": "loki", "uid": "${DS_LOKI}"}
NODE_METRICS = (
    "node_cpu_seconds_total", "node_memory_MemAvailable_bytes",
    "node_memory_MemTotal_bytes", "node_filesystem_avail_bytes",
    "node_filesystem_size_bytes", "node_network_receive_bytes_total",
    "node_network_transmit_bytes_total", "node_disk_read_bytes_total",
    "node_disk_written_bytes_total",
)
APP_METRICS = (
    "http_requests_total", "http_request_duration_seconds_sum",
    "http_request_duration_seconds_count", "http_request_duration_seconds_bucket",
    "http_request_duration_highr_seconds_bucket",
)


def get(url, params=None):
    if params:
        url += "?" + urlencode(params)
    try:
        with urlopen(url, timeout=12) as response:
            body = response.read().decode("utf-8")
            try:
                body = json.loads(body)
            except ValueError:
                pass
            return {"http_status": response.status, "body": body}
    except HTTPError as exc:
        return {"http_status": exc.code, "error": exc.read(1000).decode("utf-8", "replace")}
    except (OSError, TimeoutError) as exc:
        return {"http_status": None, "error": str(exc)}


def prom_query(base, expression):
    return get(base + "/api/v1/query", {"query": expression})


def vector(response):
    body = response.get("body", {})
    if isinstance(body, dict) and body.get("status") == "success":
        return body.get("data", {}).get("result", [])
    return []


def discover(prometheus, loki):
    now = datetime.now(timezone.utc)
    names_response = get(prometheus + "/api/v1/label/__name__/values")
    names_body = names_response.get("body", {})
    if not isinstance(names_body, dict) or names_body.get("status") != "success":
        raise RuntimeError("Prometheus metric discovery failed: " + str(names_response))
    names = set(names_body.get("data", []))
    targets_response = get(prometheus + "/api/v1/targets")
    targets_body = targets_response.get("body", {})
    if not isinstance(targets_body, dict) or targets_body.get("status") != "success":
        raise RuntimeError("Prometheus target discovery failed: " + str(targets_response))
    targets = targets_body["data"]["activeTargets"]
    observations = {
        "observed_at_utc": now.isoformat(),
        "endpoints": {"prometheus": prometheus, "loki": loki},
        "targets": [
            {key: target.get(key) for key in ("labels", "scrapeUrl", "health", "lastError", "scrapeInterval")}
            for target in targets
        ],
        "node_metrics_in_prometheus": sorted(set(NODE_METRICS) & names),
        "node_metrics_missing_from_prometheus": sorted(set(NODE_METRICS) - names),
        "servers": {},
        "application_series": {},
    }
    for ip, hostname in SERVERS.items():
        exporter = get(f"http://{ip}:9100/metrics")
        text = exporter.get("body", "")
        exported = sorted({
            line.split("{", 1)[0].split(" ", 1)[0]
            for line in text.splitlines() if line and not line.startswith("#")
        }) if isinstance(text, str) else []
        observations["servers"][ip] = {
            "hostname": hostname,
            "health": get(f"http://{ip}:8000/api/v1/health"),
            "metrics_endpoint": get(f"http://{ip}:8000/metrics"),
            "exporter_http_status": exporter["http_status"],
            "verified_exporter_metric_names": sorted(set(exported) & set(NODE_METRICS)),
            "prometheus_node_up": vector(prom_query(prometheus, f'up{{job="node",instance="{ip}:9100"}}')),
            "prometheus_node_data": vector(prom_query(prometheus, f'node_memory_MemTotal_bytes{{job="node",instance="{ip}:9100"}}')),
        }
        # A successful /metrics response can be large; retain status, not raw exposition.
        if observations["servers"][ip]["metrics_endpoint"]["http_status"] == 200:
            observations["servers"][ip]["metrics_endpoint"] = {"http_status": 200}
    for metric in APP_METRICS:
        if metric in names:
            response = prom_query(prometheus, metric + '{instance=~"192[.]168[.]0[.](156|157):8000"}')
            observations["application_series"][metric] = [item["metric"] for item in vector(response)]
    start = int((now.timestamp() - 7 * 86400) * 1_000_000_000)
    end = int(now.timestamp() * 1_000_000_000)
    observations["loki_readiness"] = get(loki + "/ready")
    observations["loki_labels_7d"] = get(loki + "/loki/api/v1/labels", {"start": start, "end": end})
    observations["loki_fastapi_series_7d"] = get(loki + "/loki/api/v1/series", {
        "match[]": '{job="fastapi",host=~"fastapi1|fastapi2"}', "start": start, "end": end,
    })
    return observations


def panel(panel_id, title, kind, x, y, w=12, h=7, description=""):
    return {"id": panel_id, "title": title, "type": kind,
            "gridPos": {"x": x, "y": y, "w": w, "h": h}, "description": description}


def text_panel(panel_id, title, content, x, y, w=12, h=5):
    result = panel(panel_id, title, "text", x, y, w, h)
    result["options"] = {"mode": "markdown", "content": content}
    return result


def metric_panel(panel_id, title, expressions, x, y, unit="short", kind="timeseries", description=""):
    result = panel(panel_id, title, kind, x, y, description=description)
    result["datasource"] = PROM_DS
    result["targets"] = [
        {"refId": chr(65 + index), "expr": expression, "legendFormat": legend,
         "editorMode": "code", "range": kind == "timeseries", "instant": kind == "stat",
         "datasource": PROM_DS}
        for index, (expression, legend) in enumerate(expressions)
    ]
    defaults = {"unit": unit, "noValue": "NO DATA", "mappings": [],
                "color": {"mode": "palette-classic"},
                "thresholds": {"mode": "absolute", "steps": [{"color": "green", "value": None}]}}
    if unit == "percent":
        defaults.update({"min": 0, "max": 100, "decimals": 1})
    if kind == "stat":
        result["options"] = {"reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
                             "colorMode": "background", "graphMode": "none", "textMode": "auto",
                             "orientation": "horizontal"}
    else:
        defaults["custom"] = {"drawStyle": "line", "lineInterpolation": "linear", "lineWidth": 2,
                               "fillOpacity": 8, "showPoints": "never", "spanNulls": False,
                               "axisCenteredZero": False, "stacking": {"mode": "none", "group": "A"}}
        result["options"] = {"legend": {"displayMode": "table", "placement": "bottom", "calcs": ["lastNotNull", "mean"]},
                             "tooltip": {"mode": "multi", "sort": "desc"}}
    result["fieldConfig"] = {"defaults": defaults, "overrides": []}
    result["transformations"] = [
        {"id": "renameByRegex", "options": {"regex": r"192\.168\.0\.156(?::[0-9]+)?", "renamePattern": "FastAPI1"}},
        {"id": "renameByRegex", "options": {"regex": r"192\.168\.0\.157(?::[0-9]+)?", "renamePattern": "FastAPI2"}},
    ]
    return result


def status_panel(panel_id, title, expression, x, y, description):
    result = metric_panel(panel_id, title, [(expression, "{{instance}}")], x, y, kind="stat", description=description)
    result["gridPos"]["h"] = 4
    result["fieldConfig"]["defaults"].update({
        "color": {"mode": "thresholds"}, "noValue": "UNKNOWN / NOT SCRAPED",
        "mappings": [{"type": "value", "options": {"0": {"text": "DOWN", "color": "red"}, "1": {"text": "UP", "color": "green"}}}],
        "thresholds": {"mode": "absolute", "steps": [{"color": "red", "value": None}, {"color": "green", "value": 1}]},
    })
    return result


def build(observations):
    missing_nodes = [ip for ip, info in observations["servers"].items() if not info["prometheus_node_data"]]
    app_series = observations["application_series"]
    requests = app_series.get("http_requests_total", [])
    # Only activate the known instrumentator schema after observing its actual labels.
    requests = [item for item in requests if all(key in item for key in ("instance", "job", "status"))]
    jobs = sorted({item["job"] for item in requests})
    app_match = 'job=~' + json.dumps("|".join(re.escape(job) for job in jobs)) + ',instance=~`(${server:regex}):8000`'
    loki_response = observations["loki_fastapi_series_7d"].get("body", {})
    log_series = loki_response.get("data", []) if isinstance(loki_response, dict) else []
    log_series = [item for item in log_series if item.get("job") == "fastapi" and item.get("host") in SERVERS.values()]
    summary = (
        f"실측 확인: `{observations['observed_at_utc']}` (UTC). "
        "필터에서 FastAPI1 / FastAPI2 / All을 선택합니다.\n\n"
        "**UP/DOWN은 Prometheus 수집 대상의 상태입니다.** DOWN만으로 서버 또는 FastAPI 장애를 단정할 수 없습니다. "
        "NO DATA / UNKNOWN은 미등록·미수집·시계열 소실이며 0으로 바꾸지 않습니다.\n\n"
        f"Node 데이터 미수집 서버: `{', '.join(missing_nodes) or '없음'}`. "
        f"FastAPI 요청 메트릭: **{'확인됨' if requests else '미수집'}**. "
        f"Loki FastAPI 스트림: **{'확인됨' if log_series else '미수집'}**. "
        "추가 설정과 실측 기록은 함께 제공된 README.md / discovery.json을 확인하세요."
    )
    panels = [text_panel(1, "CulturePick · 수집 상태 및 해석", summary, 0, 0, 24, 5)]
    node = 'job="node",instance=~`(${server:regex}):9100`'
    panels += [
        status_panel(2, "Node Exporter UP / DOWN · :9100", f"up{{{node}}}", 0, 5,
                     "1=수집 성공, 0=수집 실패. 대상이 없으면 UNKNOWN. OS 자원 수집 상태이며 FastAPI 헬스체크가 아닙니다."),
        text_panel(3, "FastAPI 연결 안내 · API :8000 / 시스템 :9100",
                   "**시스템 수집 상태:** 왼쪽 Node Exporter `:9100` 패널을 확인하세요.\n\n"
                   "**FastAPI API:** `:8000/api/v1/health`, `:8000/api/v1/ready`로 확인합니다. "
                   "이 안내는 실시간 API 상태 측정값이 아닙니다. 과거 `:8000 job=node` 수집 대상은 정리되었습니다.",
                   12, 5, h=4),
    ]
    metric_specs = [
        (4, "CPU 사용률", [(f'100 * (1 - avg by (instance) (rate(node_cpu_seconds_total{{{node},mode="idle"}}[$__rate_interval])))', "{{instance}}")], 0, 9, "percent"),
        (5, "메모리 사용률", [(f"100 * (1 - node_memory_MemAvailable_bytes{{{node}}} / node_memory_MemTotal_bytes{{{node}}})", "{{instance}}")], 12, 9, "percent"),
        (6, "디스크 공간 사용률 · 파일시스템별", [(f'100 * (1 - node_filesystem_avail_bytes{{{node},fstype!~"tmpfs|devtmpfs|overlay|squashfs",mountpoint!~"/run.*|/snap.*"}} / node_filesystem_size_bytes{{{node},fstype!~"tmpfs|devtmpfs|overlay|squashfs",mountpoint!~"/run.*|/snap.*"}})', "{{instance}} {{mountpoint}}")], 0, 16, "percent"),
        (7, "디스크 I/O · 장치별 읽기 / 쓰기", [
            (f'rate(node_disk_read_bytes_total{{{node},device!~"loop.*|ram.*|sr.*"}}[$__rate_interval])', "{{instance}} {{device}} 읽기"),
            (f'rate(node_disk_written_bytes_total{{{node},device!~"loop.*|ram.*|sr.*"}}[$__rate_interval])', "{{instance}} {{device}} 쓰기"),
        ], 12, 16, "Bps"),
        (8, "네트워크 수신 · 인터페이스별", [(f'rate(node_network_receive_bytes_total{{{node},device!~"lo|veth.*|docker.*|br-.*"}}[$__rate_interval])', "{{instance}} {{device}} RX")], 0, 23, "Bps"),
        (9, "네트워크 송신 · 인터페이스별", [(f'rate(node_network_transmit_bytes_total{{{node},device!~"lo|veth.*|docker.*|br-.*"}}[$__rate_interval])', "{{instance}} {{device}} TX")], 12, 23, "Bps"),
    ]
    for panel_id, title, expressions, x, y, unit in metric_specs:
        # Do not put unobserved metric names into dashboard queries.
        used = set(re.findall(r"\bnode_[a-zA-Z0-9_]+", " ".join(expr for expr, _ in expressions)))
        if used <= set(observations["node_metrics_in_prometheus"]):
            panels.append(metric_panel(panel_id, title, expressions, x, y, unit,
                                       description="확인된 Node Exporter 메트릭. 두 서버의 :9100을 job=node로 수집해야 데이터가 표시됩니다. 디스크 I/O는 장치별이며 dm-0과 sda를 합산하지 않습니다."))
        else:
            panels.append(text_panel(panel_id, title + " · 수집 대기", "Prometheus에서 필요한 Node 메트릭이 확인되지 않았습니다. README.md를 확인하세요.", x, y, h=7))
    rate = f"sum by (instance) (rate(http_requests_total{{{app_match}}}[$__rate_interval]))"
    app_specs = [
        (10, "FastAPI 요청 수 · 선택 기간 증가량", "선택 기간 내 요청 증가량입니다. increase()의 보간 때문에 소수일 수 있습니다.",
         [(f"sum by (instance) (increase(http_requests_total{{{app_match}}}[$__range]))", "{{instance}}")], 0, 30, "short", "stat"),
        (11, "FastAPI RPS", "서버별 초당 요청 수입니다.", [(rate, "{{instance}}")], 12, 30, "reqps", "timeseries"),
        (12, "FastAPI 응답 시간 · 평균 / p95", "초 단위 지연 시간. p95는 실제 관측된 histogram bucket이 있을 때만 표시합니다.", [], 0, 37, "s", "timeseries"),
        (13, "HTTP 오류율 · 4xx / 5xx", "4xx 및 5xx 요청 비율. 요청이 없으면 NO DATA이며, 요청은 있고 오류 시계열만 없으면 0%입니다.", [], 12, 37, "percent", "timeseries"),
    ]
    same_schema = lambda metric: any(row.get("job") in jobs for row in app_series.get(metric, []))
    latency = []
    if same_schema("http_request_duration_seconds_sum") and same_schema("http_request_duration_seconds_count"):
        count = f"sum by (instance) (rate(http_request_duration_seconds_count{{{app_match}}}[$__rate_interval]))"
        latency.append((f"sum by (instance) (rate(http_request_duration_seconds_sum{{{app_match}}}[$__rate_interval])) / ({count} > 0)", "{{instance}} 평균"))
    for bucket in ("http_request_duration_highr_seconds_bucket", "http_request_duration_seconds_bucket"):
        if same_schema(bucket) and any(row.get("le") == "+Inf" for row in app_series.get(bucket, [])):
            latency.append((f"histogram_quantile(0.95, sum by (instance, le) (rate({bucket}{{{app_match}}}[$__rate_interval])))", "{{instance}} p95"))
            break
    errors = []
    for code in ("4", "5"):
        numerator = f'sum by (instance) (rate(http_requests_total{{{app_match},status=~"{code}.."}}[$__rate_interval]))'
        errors.append((f"100 * (({numerator}) or on (instance) (0 * ({rate}))) / ({rate} > 0)", "{{instance}} " + code + "xx"))
    for panel_id, title, description, expressions, x, y, unit, kind in app_specs:
        if panel_id == 12:
            expressions = latency
        if panel_id == 13:
            expressions = errors
        if requests and expressions:
            panels.append(metric_panel(panel_id, title, expressions, x, y, unit, kind, description))
        else:
            panels.append(text_panel(panel_id, title + " · 수집 대기",
                                     "**수집 데이터가 없습니다.** 확인되지 않은 메트릭의 쿼리는 만들지 않았습니다.\n\n"
                                     "FastAPI 계측 및 Prometheus 수집을 설정한 뒤 생성 스크립트를 다시 실행하세요. "
                                     "요청 수/RPS/오류율에는 요청 카운터와 상태 코드, 응답 시간에는 duration sum/count 또는 histogram이 필요합니다.", x, y, h=7))
    panels.append(text_panel(14, "Alloy → Loki · 로그 수집 상태",
                             "Loki에서 확인된 스트림에만 로그 쿼리를 연결합니다. "
                             + ("FastAPI 스트림이 확인되었습니다. 서버 필터와 로그 검색어를 사용할 수 있습니다." if log_series else
                                "**현재 FastAPI 스트림이 없어 아래 로그 패널의 쿼리를 비워 두었습니다.** "
                                "Alloy의 /var/log/app.log 파일 경로와 읽기 권한을 확인하고, 새 로그가 수집된 뒤 JSON을 재생성하세요. "
                                "설정 파일의 host=fastapi1/fastapi2는 확인했지만 Loki 수집 라벨로 확인된 상태는 아닙니다."), 0, 44, 24, 4))
    logs = panel(15, "FastAPI 로그" + ("" if log_series else " · 수집 대기"), "logs", 0, 48, 24, 12,
                 "Alloy에서 Loki로 들어온 실제 로그. server_ip는 host와 IP의 고정 대응을 이용해 쿼리 시점에 만드는 필터용 라벨입니다.")
    logs.update({"datasource": LOKI_DS, "targets": [], "options": {
        "showTime": True, "showLabels": True, "showCommonLabels": False,
        "wrapLogMessage": True, "prettifyLogMessage": False, "enableLogDetails": True,
        "sortOrder": "Descending", "dedupStrategy": "none",
    }})
    if log_series:
        expression = ('{job="fastapi",host=~"fastapi1|fastapi2"}'
                      ' | label_format server_ip=`{{ if eq .host "fastapi1" }}192.168.0.156{{ else if eq .host "fastapi2" }}192.168.0.157{{ end }}`'
                      ' | server_ip=~`${server:regex}` |= ${search:doublequote}')
        logs["targets"] = [{"refId": "A", "expr": expression, "queryType": "range", "editorMode": "code", "datasource": LOKI_DS}]
    panels.append(logs)
    return {
        "__inputs": [
            {"name": "DS_PROMETHEUS", "label": "Prometheus", "description": observations["endpoints"]["prometheus"], "type": "datasource", "pluginId": "prometheus", "pluginName": "Prometheus"},
            {"name": "DS_LOKI", "label": "Loki", "description": observations["endpoints"]["loki"], "type": "datasource", "pluginId": "loki", "pluginName": "Loki"},
        ],
        "annotations": {"list": []}, "editable": True, "id": None,
        "uid": "culturepick-fastapi-servers", "title": "CulturePick · FastAPI1 / FastAPI2",
        "description": "실측 메트릭/라벨에 기반한 두 FastAPI 서버 모니터링. 미수집 항목은 수집 대기 상태로 표시합니다.",
        "tags": ["culturepick", "fastapi", "node-exporter", "loki"],
        "schemaVersion": 39, "version": 1, "timezone": "browser", "refresh": "30s",
        "time": {"from": "now-1h", "to": "now"},
        "timepicker": {"refresh_intervals": ["15s", "30s", "1m", "5m"]},
        "templating": {"list": [
            {"name": "server", "label": "서버", "type": "custom", "query": "FastAPI1 : 192.168.0.156,FastAPI2 : 192.168.0.157",
             "multi": True, "includeAll": True, "allValue": "192[.]168[.]0[.](156|157)",
             "current": {"selected": True, "text": ["All"], "value": ["$__all"]},
             "options": [{"text": "All", "value": "$__all", "selected": True},
                         {"text": "FastAPI1", "value": "192.168.0.156", "selected": False},
                         {"text": "FastAPI2", "value": "192.168.0.157", "selected": False}], "hide": 0},
            {"name": "search", "label": "로그 검색어", "type": "textbox", "query": "", "current": {"text": "", "value": ""}, "options": [], "hide": 0},
        ]},
        "panels": panels,
    }


def validate(dashboard, prometheus, loki):
    ids = [item["id"] for item in dashboard["panels"]]
    assert len(ids) == len(set(ids)), "Duplicate panel IDs"
    assert dashboard["id"] is None and dashboard["schemaVersion"] == 39
    for index, left in enumerate(dashboard["panels"]):
        a = left["gridPos"]
        assert 0 <= a["x"] and a["x"] + a["w"] <= 24
        for right in dashboard["panels"][index + 1:]:
            b = right["gridPos"]
            assert not (a["x"] < b["x"] + b["w"] and b["x"] < a["x"] + a["w"] and
                        a["y"] < b["y"] + b["h"] and b["y"] < a["y"] + a["h"]), "Overlapping panels"
    jobs = []
    for item in dashboard["panels"]:
        for target in item.get("targets", []):
            for label, regex in [("FastAPI1", r"192\.168\.0\.156"), ("FastAPI2", r"192\.168\.0\.157"), ("All", "192[.]168[.]0[.](156|157)")]:
                expr = target["expr"].replace("${server:regex}", regex).replace("$__rate_interval", "1m").replace("$__range", "1h").replace("${search:doublequote}", '""')
                jobs.append((item["id"], label, item["type"], expr))

    def check(job):
        panel_id, selection, kind, expr = job
        if kind == "logs":
            result = get(loki + "/loki/api/v1/query_range", {"query": expr, "since": "1h", "limit": 100})
        else:
            result = prom_query(prometheus, expr)
        body = result.get("body", {})
        success = result["http_status"] == 200 and isinstance(body, dict) and body.get("status") == "success"
        return {"panel_id": panel_id, "server": selection, "success": success,
                "series_count": len(body.get("data", {}).get("result", [])) if success else None,
                **({"error": result} if not success else {})}

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(check, jobs))
    failed = [item for item in results if not item["success"]]
    print(json.dumps({"checked_queries": len(results), "failed_queries": len(failed), "results": results}, indent=2))
    if failed:
        raise RuntimeError("Live query validation failed")
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prometheus", default="http://192.168.0.159:9090")
    parser.add_argument("--loki", default="http://192.168.0.158:3101")
    parser.add_argument("--validate-only", action="store_true", help="Validate existing JSON without changing files")
    args = parser.parse_args()
    dashboard_path = HERE / "culturepick-fastapi.dashboard.json"
    if args.validate_only:
        validate(json.loads(dashboard_path.read_text(encoding="utf-8")), args.prometheus, args.loki)
        return
    observations = discover(args.prometheus.rstrip("/"), args.loki.rstrip("/"))
    dashboard = build(observations)
    observations["dashboard_query_validation"] = validate(dashboard, args.prometheus, args.loki)
    dashboard_path.write_text(json.dumps(dashboard, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (HERE / "discovery.json").write_text(json.dumps(observations, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Saved:", dashboard_path, "and discovery.json")


if __name__ == "__main__":
    main()
