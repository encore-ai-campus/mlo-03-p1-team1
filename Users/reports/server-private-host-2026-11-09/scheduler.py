"""001~100 순서로 시작하고, 최대 5개 세션이 겹쳐 실행되는 순환 스케줄러."""
import asyncio
import copy
import json
import os
import random
from contextlib import contextmanager
from pathlib import Path

from src.codex_runner import create_behavior_probabilities
from src.persona_loader import load_persona
from src.simulator import now, run_simulation

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs"
PERSONA_FILES = tuple(f"persona_{number:03d}.md" for number in range(1, 101))
MAX_CONCURRENT = 5
SESSION_SECONDS = (60.0, 300.0)
START_INTERVAL_SECONDS = (5.0, 45.0)
ACTION_WAIT_SECONDS = (3.0, 12.0)
REST_SECONDS = 30 * 60


@contextmanager
def scheduler_lock():
    """OS 파일 잠금은 프로세스 종료 시 해제되며 중복 스케줄러를 막습니다."""
    RUNS.mkdir(exist_ok=True)
    with (RUNS / "scheduler.lock").open("a+b") as lock:
        if os.name == "nt":
            import msvcrt
            if lock.seek(0, 2) == 0:
                lock.write(b"0")
                lock.flush()
            lock.seek(0)
            try:
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise RuntimeError("이미 실행 중인 Oddinary 스케줄러가 있습니다.") from exc
        else:
            import fcntl
            try:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise RuntimeError("이미 실행 중인 Oddinary 스케줄러가 있습니다.") from exc
        try:
            yield
        finally:
            if os.name == "nt":
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def prepare_personas(rules):
    # 먼저 전원 검증: 파일 누락/잘못된 프로필을 조용히 건너뛰지 않습니다.
    personas = [load_persona(filename, rules) for filename in PERSONA_FILES]
    entries = []
    for persona in personas:
        output = create_behavior_probabilities(persona, rules)
        entries.append((persona, json.loads(output.read_text(encoding="utf-8"))))
    return entries


async def run_cycle(entries, rules, *, rng=None, start_interval=START_INTERVAL_SECONDS,
                    session_seconds=SESSION_SECONDS):
    expected_ids = [Path(filename).stem for filename in PERSONA_FILES]
    if [persona["persona_id"] for persona, _ in entries] != expected_ids:
        raise ValueError("회차에는 persona_001~persona_100이 순서대로 정확히 한 번씩 필요합니다.")
    rng = rng or random.Random()
    slots = asyncio.Semaphore(MAX_CONCURRENT)
    active = set()
    tasks = []
    results = {}

    async def execute(persona, probabilities, duration, started):
        persona_id = persona["persona_id"]
        active.add(persona_id)
        started.set()
        print(f"[{now()}] 시작 {persona_id}; 동시 활동 {len(active)}/{MAX_CONCURRENT}; 최대 {duration:.1f}초", flush=True)
        session_rules = copy.deepcopy(rules)
        session_rules["site_url"] = "https://www.aiready.p-e.kr/"
        session_rules["session"].update(
            duration_seconds=duration, max_minutes=5, wait_seconds=ACTION_WAIT_SECONDS,
            headless=True, chromium_only=True, unattended=True,
        )
        try:
            result = await run_simulation(persona, session_rules, probabilities)
            results[persona_id] = {"persona_id": persona_id, "status": "종료",
                                   "end_reason": (result or {}).get("end_reason", "종료")}
        except Exception as exc:
            # 한 세션의 실패가 나머지 99명의 시작을 막지 않게 합니다.
            results[persona_id] = {"persona_id": persona_id, "status": "실패", "end_reason": str(exc)[:500]}
        finally:
            active.discard(persona_id)
            slots.release()
            print(f"[{now()}] 종료 {persona_id}; 동시 활동 {len(active)}/{MAX_CONCURRENT}", flush=True)

    try:
        for index, (persona, probabilities) in enumerate(entries):
            await slots.acquire()
            started = asyncio.Event()
            duration = min(300.0, rng.uniform(*session_seconds))
            tasks.append(asyncio.create_task(execute(persona, probabilities, duration, started)))
            # 실제 세션 시작 순서도 파일 순서와 일치시킵니다.
            await started.wait()
            if index < len(entries) - 1:
                await asyncio.sleep(rng.uniform(*start_interval))
        await asyncio.gather(*tasks)
    finally:
        # 중단 시에도 브라우저 정리가 끝나기 전에 다음 회차가 시작되지 않습니다.
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    if set(results) != set(expected_ids):
        raise RuntimeError("종료 결과가 없는 페르소나가 있습니다.")
    return [results[persona_id] for persona_id in expected_ids]


async def run_scheduler(rules, *, once=False):
    with scheduler_lock():
        # 확률 생성은 이벤트 루프 밖에서 한 번만 수행하며 기존 파일을 재사용합니다.
        entries = await asyncio.to_thread(prepare_personas, rules)
        cycle = 0
        while True:
            cycle += 1
            started_at = now()
            results = await run_cycle(entries, rules)
            (RUNS / "scheduler_cycle.json").write_text(json.dumps(
                {"cycle": cycle, "started_at": started_at, "ended_at": now(), "results": results},
                ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[{now()}] 회차 {cycle}: 100명 전원 종료", flush=True)
            if once:
                return results
            print(f"[{now()}] 30분 휴식 후 persona_001부터 다시 시작", flush=True)
            await asyncio.sleep(REST_SECONDS)
