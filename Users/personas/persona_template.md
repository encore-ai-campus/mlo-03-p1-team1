# 페르소나 작성 안내

아래 JSON 블록만 수정하세요. 문화 카테고리는 6개 중 한 개 이상 선택해야 합니다. 성별·나이·거주지·직업·MBTI는 선택 정보라 모르면 `null`로 둡니다. 태그는 선택한 문화 카테고리에 연결된 세부 장르 태그와 전체 공통 태그에서만 골라 적습니다. 선택하지 않은 카테고리의 세부 장르 태그는 사용할 수 없습니다. 태그는 한 번 저장한 뒤 시뮬레이션 중에는 바꾸지 않습니다.

예산과 행동 성향은 사이트 가입 화면에 입력하지 않고 행동 확률을 조정할 때 사용합니다.

```json
{
  "persona_id": "persona_001",
  "signup_profile": {
    "gender": null,
    "age": null,
    "region": null,
    "occupation": null,
    "mbti": null,
    "cultural_categories": [],
    "tags": []
  },
  "simulation_traits": {
    "monthly_culture_budget_krw": null,
    "price_sensitivity": null,
    "culture_activity_frequency": null,
    "search_tendency": null,
    "favorite_tendency": null,
    "review_tendency": null,
    "purchase_tendency": null,
    "companions": []
  }
}
```
