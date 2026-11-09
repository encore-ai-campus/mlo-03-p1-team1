"""Run one full 100-persona pass with up to 20 sessions and 3 headed browsers."""
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path

from src import scheduler, simulator
from src.persona_loader import load_rules

ROOT = Path(__file__).resolve().parents[1]
RUN_DIR = ROOT / "runs" / "server_100_20261109"
LOG_DIR = ROOT / "logs" / "server_100_20261109"
RUN_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

HEADLESS_RUN_SIMULATION = simulator.run_simulation

async def run_with_three_windows(persona, rules, probabilities):
    rules["session"]["headless"] = persona["persona_id"] not in {
        "persona_001", "persona_002", "persona_003"
    }
    rules["session"]["chromium_only"] = True
    return await HEADLESS_RUN_SIMULATION(persona, rules, probabilities)

async def main():
    scheduler.RUNS = RUN_DIR
    simulator.RUNS = RUN_DIR
    scheduler.MAX_CONCURRENT = 20
    scheduler.SESSION_SECONDS = (60.0, 60.0)
    scheduler.START_INTERVAL_SECONDS = (0.1, 0.4)
    # run_cycle captures its defaults at definition time; override that tuple too.
    scheduler.run_cycle.__kwdefaults__["start_interval"] = (0.1, 0.4)
    scheduler.run_cycle.__kwdefaults__["session_seconds"] = (60.0, 60.0)
    scheduler.run_simulation = run_with_three_windows
    rules = load_rules()
    entries = await asyncio.to_thread(scheduler.prepare_personas, rules)
    cycle = 0
    while True:
        cycle += 1
        started = datetime.now(timezone.utc).isoformat()
        results = await scheduler.run_cycle(entries, rules)
        output = {
            "cycle": cycle,
            "started_at": started,
            "ended_at": datetime.now(timezone.utc).isoformat(),
            "persona_count": len(results),
            "headless_false": ["persona_001", "persona_002", "persona_003"],
            "max_concurrent": 20,
            "results": results,
        }
        summary = RUN_DIR / f"cycle_{cycle:04d}.json"
        summary.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"회차 {cycle} 완료: {len(results)}명; 결과: {summary}", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
