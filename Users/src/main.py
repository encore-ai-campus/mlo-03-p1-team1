"""실행 예: python -m src.main persona_001.md"""
import argparse
import asyncio
import json
from src.codex_runner import create_behavior_probabilities
from src.persona_loader import load_persona, load_rules
from src.simulator import run_simulation
from src.scheduler import run_scheduler


def main() -> None:
    parser = argparse.ArgumentParser(description="Oddinary 페르소나를 순환 실행합니다.")
    parser.add_argument("persona_file", nargs="?", help="생략하면 001~100 순환 실행. 지정하면 기존 단일 실행.")
    parser.add_argument("--once", action="store_true", help="스케줄러를 한 회차만 실행합니다.")
    args = parser.parse_args()

    rules = load_rules()
    if args.persona_file is None:
        asyncio.run(run_scheduler(rules, once=args.once))
        return
    persona = load_persona(args.persona_file, rules)
    output = create_behavior_probabilities(persona, rules)
    print(f"페르소나: {persona['persona_id']}")
    print(f"확률 파일: {output}")
    asyncio.run(run_simulation(persona, rules, json.loads(output.read_text(encoding="utf-8"))))


if __name__ == "__main__":
    main()
