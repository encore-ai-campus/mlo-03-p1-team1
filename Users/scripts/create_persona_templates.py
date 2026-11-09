"""빈 페르소나 Markdown 파일을 생성합니다. 기존 파일은 덮어쓰지 않습니다."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "personas" / "persona_template.md"
PERSONAS = ROOT / "personas"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=100, help="생성할 페르소나 수 (기본값: 100)")
    args = parser.parse_args()
    if args.count < 1:
        parser.error("--count는 1 이상이어야 합니다.")

    template_text = TEMPLATE.read_text(encoding="utf-8")
    created = 0
    skipped = 0
    for number in range(1, args.count + 1):
        persona_id = f"persona_{number:03d}"
        path = PERSONAS / f"{persona_id}.md"
        if path.exists():
            skipped += 1
            continue
        text = template_text.replace('"persona_id": "persona_001"', f'"persona_id": "{persona_id}"')
        path.write_text(text, encoding="utf-8")
        created += 1
    print(f"생성: {created}개, 기존 파일이라 건너뜀: {skipped}개")


if __name__ == "__main__":
    main()
