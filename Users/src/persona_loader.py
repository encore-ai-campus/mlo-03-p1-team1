"""페르소나 Markdown의 JSON 블록과 공통 규칙을 읽고 검증합니다."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PERSONAS_DIR = ROOT / "personas"
RULES_PATH = ROOT / "config" / "behavior_rules.json"
JSON_BLOCK = re.compile(r"```json\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)


def load_rules() -> dict:
    rules = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    tags = rules["tag_catalog"]
    flat_tags = [tag for group in tags["category_tags"].values() for tag in group]
    flat_tags += [tag for group in tags["common_tags"].values() for tag in group]
    if len(flat_tags) != rules["expected_tag_count"] or len(set(flat_tags)) != len(flat_tags):
        raise ValueError("설정의 태그 수 또는 중복을 확인하세요.")
    return rules


def load_persona(filename: str, rules: dict | None = None) -> dict:
    if Path(filename).name != filename or not filename.endswith(".md"):
        raise ValueError("페르소나 파일명만 입력하세요. 예: persona_001.md")
    path = PERSONAS_DIR / filename
    if not path.is_file():
        raise FileNotFoundError(f"페르소나 파일을 찾을 수 없습니다: {path}")

    text = path.read_text(encoding="utf-8")
    match = JSON_BLOCK.search(text)
    if not match:
        raise ValueError(f"{filename}: ```json ... ``` 블록이 필요합니다.")
    persona = json.loads(match.group(1))
    rules = rules or load_rules()

    if persona.get("persona_id") != path.stem:
        raise ValueError("persona_id는 파일명과 같아야 합니다.")
    profile = persona.get("signup_profile")
    if not isinstance(profile, dict):
        raise ValueError("signup_profile 객체가 필요합니다.")
    categories = profile.get("cultural_categories")
    for field in ("gender", "age", "region", "occupation", "mbti"):
        if profile.get(field) is None:
            raise ValueError(f"signup_profile.{field} 값이 필요합니다.")
    allowed_categories = set(rules["cultural_categories"])
    if not isinstance(categories, list) or not categories:
        raise ValueError("cultural_categories에는 가입 시 선택할 카테고리를 1개 이상 입력하세요.")
    if len(categories) != len(set(categories)) or not set(categories) <= allowed_categories:
        raise ValueError("cultural_categories 값이 올바르지 않거나 중복되었습니다.")

    tag_catalog = rules["tag_catalog"]
    category_specific_tags = {
        tag
        for category in categories
        for tag in tag_catalog["category_tags"][category]
    }
    common_tags = {tag for group in tag_catalog["common_tags"].values() for tag in group}
    allowed_tags = category_specific_tags | common_tags
    selected_tags = profile.get("tags", [])
    if not isinstance(selected_tags, list) or len(selected_tags) != len(set(selected_tags)):
        raise ValueError("tags는 중복 없는 배열이어야 합니다.")
    invalid_tags = set(selected_tags) - allowed_tags
    if invalid_tags:
        raise ValueError(
            "선택 카테고리의 세부 태그 또는 공통 태그만 사용할 수 있습니다: "
            + ", ".join(sorted(invalid_tags))
        )
    if len(selected_tags) != 10:
        raise ValueError("tags에는 중복 없는 표준 태그를 정확히 10개 입력하세요.")
    return persona
