# 페르소나 작성 안내

테스트용 합성 사용자 데이터입니다. 가입 취향은 고정되며, 예산과 행동 성향은 시뮬레이션 판단에만 ```json
{
  "persona_id": "persona_100",
  "signup_profile": {
    "gender": "female",
    "age": 55,
    "region": "세종",
    "occupation": "바리스타",
    "mbti": "ENTJ",
    "cultural_categories": [
      "음악",
      "무용"
    ],
    "tags": [
      "합창",
      "잔잔한",
      "자연",
      "R&B",
      "이야기",
      "유서 깊은 공간",
      "서정적인",
      "록",
      "실험적인",
      "유쾌한"
    ]
  },
  "simulation_traits": {
    "monthly_culture_budget_krw": 180000,
    "price_sensitivity": "low",
    "culture_activity_frequency": "high",
    "search_tendency": "high",
    "favorite_tendency": "high",
    "review_tendency": "high",
    "purchase_tendency": "medium",
    "companions": [
      "가족"
    ],
    "personality": "사람들과 함께 즐기고 생생한 현장 분위기를 좋아하는 편",
    "expected_behavior": "상세 페이지와 태그를 살펴본 뒤 비슷한 행사를 연이어 조회"
  }
}
```