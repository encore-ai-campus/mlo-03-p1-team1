"""확률을 사용해 다음 행동 또는 카테고리를 선택합니다."""
import random


def choose(probabilities: dict[str, float], allowed: set[str] | None = None) -> str:
    choices = {key: value for key, value in probabilities.items() if value > 0 and (allowed is None or key in allowed)}
    if not choices:
        raise ValueError("선택 가능한 항목이 없습니다.")
    return random.choices(list(choices), weights=list(choices.values()), k=1)[0]
