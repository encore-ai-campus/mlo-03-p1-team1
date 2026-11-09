"""Codex CLI로 페르소나별 행동·카테고리 확률을 생성합니다."""
import json
import math
import shutil
import subprocess
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "config" / "behavior_output.schema.json"
RUNS_DIR = ROOT / "runs"


def _validate_distribution(name: str, values: dict, expected_keys: set[str]) -> None:
    if not isinstance(values, dict) or set(values) != expected_keys:
        raise ValueError(f"{name}의 키가 설정과 일치하지 않습니다.")
    for key, value in values.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError(f"{name}.{key}는 0~1 사이의 숫자여야 합니다.")
    if not math.isclose(sum(values.values()), 1.0, abs_tol=0.01):
        raise ValueError(f"{name}의 합은 1.0이어야 합니다.")


def create_behavior_probabilities(persona: dict, rules: dict) -> Path:
    persona_id = persona["persona_id"]
    RUNS_DIR.mkdir(exist_ok=True)
    output_path = RUNS_DIR / f"{persona_id}_behavior.json"
    if not output_path.is_file() and shutil.which("codex"):
        prompt = f"""페르소나별 행동 및 탐색 확률 JSON만 반환하세요. JSON Schema를 따르세요.
가입 관심 카테고리와 태그는 변경하지 마세요. 여섯 카테고리 전체의 확률 합은 1이며 관심 카테고리는 높게, 나머지는 낮게 배정하세요.
행동 확률도 합계 1입니다. 예산으로 직업·소득을 추론하지 마세요. 실제 고객 통계가 아닌 시뮬레이션입니다.
기본 설정: {json.dumps(rules, ensure_ascii=False)}
페르소나: {json.dumps(persona, ensure_ascii=False)}"""
        command = ["codex", "exec", "--sandbox", "read-only", "--skip-git-repo-check", "--output-schema", str(SCHEMA_PATH), "--output-last-message", str(output_path), prompt]
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=180, check=False)
        if result.returncode != 0 or not output_path.is_file():
            print("codex exec 실패, 설정 기반 Python 확률 생성으로 전환합니다.")
            output_path.unlink(missing_ok=True)
    if not output_path.is_file():
        profile = persona["signup_profile"]
        traits = persona["simulation_traits"]
        rng = random.Random(persona_id)
        base = rules["base_action_probabilities"]
        action_weights = dict(base)
        for action, trait in rules["trait_action_weights"].items():
            level = traits.get(trait, "medium")
            action_weights[action] *= rules["trait_multipliers"][level]
        action_total = sum(action_weights.values())
        action_probs = {key: round(value/action_total, 6) for key, value in action_weights.items()}
        cats = rules["cultural_categories"]
        category_weights = {c: (rules["category_interest_weight"] if c in profile["cultural_categories"] else rules["category_discovery_weight"]) for c in cats}
        for c in cats:
            if c in profile["cultural_categories"]:
                category_weights[c] *= 1 + 0.08 * sum(tag in rules["tag_catalog"]["category_tags"][c] for tag in profile["tags"])
        category_total = sum(category_weights.values())
        category_probs = {key: value/category_total for key,value in category_weights.items()}
        data = {"persona_id": persona_id, "action_probabilities": action_probs, "category_probabilities": category_probs}
        output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    data = json.loads(output_path.read_text(encoding="utf-8"))
    if data.get("persona_id") != persona_id:
        raise ValueError("생성 결과의 persona_id가 입력 페르소나와 다릅니다.")
    _validate_distribution("action_probabilities", data.get("action_probabilities"), set(rules["base_action_probabilities"]))
    _validate_distribution("category_probabilities", data.get("category_probabilities"), set(rules["cultural_categories"]))
    return output_path
