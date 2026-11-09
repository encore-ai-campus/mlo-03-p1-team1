# 페르소나 파일

- `persona_001.md`부터 `persona_100.md`까지 사용자마다 하나씩 작성합니다.
- 각 파일의 JSON 블록을 채우세요. `persona_id`는 파일명과 같아야 합니다.
- `signup_profile.cultural_categories`는 가입 필수 취향이므로 실제 선택값을 1개 이상 넣습니다.
- `signup_profile.tags`에는 선택한 카테고리의 세부 장르 태그와 모든 카테고리에 공통으로 적용되는 태그만 넣습니다. 선택하지 않은 카테고리의 세부 장르 태그는 넣지 않습니다.
- 카테고리별 태그와 공통 태그의 전체 목록은 `config/behavior_rules.json`에서 확인합니다.
- 선택 항목을 입력하지 않는 페르소나는 성별·나이·거주지·직업·MBTI에 `null`을 넣습니다.
- `simulation_traits`는 사이트 가입 정보가 아니라 행동 판단 기준입니다.
