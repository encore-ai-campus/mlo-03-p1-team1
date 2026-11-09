import asyncio
import contextlib
import copy
import io
import json
import random
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from src import codex_runner, scheduler, simulator
from src.persona_loader import load_persona, load_rules


class SchedulerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.rules = load_rules()
        self.entries = [({"persona_id": Path(name).stem}, {"unchanged": index})
                        for index, name in enumerate(scheduler.PERSONA_FILES)]

    async def test_all_100_start_in_order_with_five_slots_even_after_failure(self):
        started, ended, counts = [], [], []
        active = set()
        original_rules = copy.deepcopy(self.rules)

        async def run(persona, rules, probabilities):
            persona_id = persona["persona_id"]
            self.assertNotIn(persona_id, active)
            active.add(persona_id)
            started.append(persona_id)
            counts.append(len(active))
            self.assertTrue(rules["session"]["headless"])
            self.assertTrue(rules["session"]["chromium_only"])
            self.assertLessEqual(rules["session"]["duration_seconds"], 300)
            self.assertEqual(rules["site_url"], "https://www.aiready.p-e.kr/")
            self.assertIs(probabilities, self.entries[int(persona_id[-3:]) - 1][1])
            try:
                await asyncio.sleep(0.005)
                if persona_id == "persona_017":
                    raise RuntimeError("injected session failure")
                return {"end_reason": "done"}
            finally:
                active.remove(persona_id)
                ended.append(persona_id)

        with patch.object(scheduler, "run_simulation", side_effect=run), contextlib.redirect_stdout(io.StringIO()):
            results = await scheduler.run_cycle(self.entries, self.rules, rng=random.Random(4), start_interval=(0, 0))
        self.assertEqual(started, [item[0]["persona_id"] for item in self.entries])
        self.assertEqual(len(set(ended)), 100)
        self.assertEqual(len(results), 100)
        self.assertEqual(results[16]["status"], "실패")
        self.assertEqual(max(counts), 5)
        self.assertFalse(active)
        self.assertEqual(self.rules, original_rules)

    async def test_invalid_roster_is_rejected_before_any_session_starts(self):
        with patch.object(scheduler, "run_simulation", new_callable=AsyncMock) as run:
            for entries in (self.entries[:-1], self.entries[::-1], self.entries + self.entries[:1]):
                with self.assertRaises(ValueError):
                    await scheduler.run_cycle(entries, self.rules)
            run.assert_not_awaited()

    async def test_shutdown_waits_for_active_session_cleanup(self):
        started, cleaned = [], []

        async def run(persona, rules, probabilities):
            started.append(persona["persona_id"])
            try:
                await asyncio.Event().wait()
            finally:
                await asyncio.sleep(0)
                cleaned.append(persona["persona_id"])

        with patch.object(scheduler, "run_simulation", side_effect=run), contextlib.redirect_stdout(io.StringIO()):
            task = asyncio.create_task(scheduler.run_cycle(self.entries, self.rules, start_interval=(0, 0)))
            while len(started) < 5:
                await asyncio.sleep(0)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertEqual(set(started), set(cleaned))
        self.assertEqual(len(started), 5)

    async def test_two_hour_rest_only_after_round_completion_then_restarts(self):
        trace = []
        results = [{"persona_id": entry[0]["persona_id"]} for entry in self.entries]

        async def cycle(entries, rules):
            trace.append("all_100_finished")
            self.assertIs(entries, self.entries)
            return results

        async def sleep(seconds):
            self.assertEqual(seconds, 7200)
            self.assertEqual(trace[-1], "all_100_finished")
            trace.append("rest")
            if trace.count("rest") == 2:
                raise asyncio.CancelledError

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(scheduler, "RUNS", root), patch.object(scheduler, "scheduler_lock", contextlib.nullcontext), \
                    patch.object(scheduler, "prepare_personas", return_value=self.entries), \
                    patch.object(scheduler, "run_cycle", side_effect=cycle), \
                    patch.object(scheduler.asyncio, "sleep", side_effect=sleep), contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(asyncio.CancelledError):
                    await scheduler.run_scheduler(self.rules)
            self.assertEqual(json.loads((root / "scheduler_cycle.json").read_text(encoding="utf-8"))["cycle"], 2)
        self.assertEqual(trace, ["all_100_finished", "rest", "all_100_finished", "rest"])

    async def test_once_returns_after_all_users_without_rest(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(scheduler, "RUNS", Path(directory)), \
                    patch.object(scheduler, "scheduler_lock", contextlib.nullcontext), \
                    patch.object(scheduler, "prepare_personas", return_value=self.entries), \
                    patch.object(scheduler, "run_cycle", new_callable=AsyncMock, return_value=["done"]), \
                    patch.object(scheduler.asyncio, "sleep", new_callable=AsyncMock) as sleep, \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(await scheduler.run_scheduler(self.rules, once=True), ["done"])
                sleep.assert_not_awaited()

    def test_process_lock_rejects_second_scheduler_and_is_released(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(scheduler, "RUNS", Path(directory)):
            with scheduler.scheduler_lock():
                with self.assertRaises(RuntimeError):
                    with scheduler.scheduler_lock():
                        self.fail("duplicate scheduler acquired the lock")
            with scheduler.scheduler_lock():
                pass

    def test_all_actual_persona_files_load_without_modification(self):
        self.assertEqual(len([load_persona(name, self.rules) for name in scheduler.PERSONA_FILES]), 100)

    def test_missing_persona_fails_preflight_before_probability_generation(self):
        with patch.object(scheduler, "load_persona", side_effect=FileNotFoundError("missing persona")), \
                patch.object(scheduler, "create_behavior_probabilities") as generate:
            with self.assertRaises(FileNotFoundError):
                scheduler.prepare_personas(self.rules)
            generate.assert_not_called()

    def test_existing_probabilities_are_not_regenerated_even_with_codex_installed(self):
        persona = load_persona("persona_001.md", self.rules)
        content = (codex_runner.RUNS_DIR / "persona_001_behavior.json").read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "persona_001_behavior.json"
            output.write_bytes(content)
            with patch.object(codex_runner, "RUNS_DIR", Path(directory)), \
                    patch.object(codex_runner.shutil, "which", return_value="codex"), \
                    patch.object(codex_runner.subprocess, "run") as command:
                self.assertEqual(codex_runner.create_behavior_probabilities(persona, self.rules), output)
                command.assert_not_called()
            self.assertEqual(output.read_bytes(), content)

    async def test_deadline_cancels_activity_waits_for_cleanup_and_saves_result(self):
        persona = load_persona("persona_001.md", self.rules)
        self.rules["session"]["duration_seconds"] = 0.01
        sim = simulator.Simulator(persona, self.rules, {})
        cleaned = asyncio.Event()

        async def activity():
            try:
                await asyncio.Event().wait()
            finally:
                cleaned.set()

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(sim, "_run_browser", side_effect=activity), \
                    patch.object(simulator, "ROOT", root), patch.object(simulator, "RUNS", root), \
                    contextlib.redirect_stdout(io.StringIO()):
                result = await sim.run()
            self.assertTrue(cleaned.is_set())
            self.assertEqual(result["end_reason"], "세션 시간 제한")
            self.assertTrue((root / "persona_001_simulation.json").is_file())


if __name__ == "__main__":
    unittest.main()
