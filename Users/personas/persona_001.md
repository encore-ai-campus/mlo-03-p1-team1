# 페르소나 작성 안내

테스트용 합성 사용자 데이터입니다. 가입 취향은 고정되며, 예산과 행동 성향은 시뮬레이션 판단에만 ```json
{
  "persona_id": "persona_001",
  "signup_profile": {
    "gender": "prefer_not_to_say",
    "age": 35,
    "region": "서울",
    "occupation": "박물관 교육사",
    "mbti": "ISFJ",
    "cultural_categories": [
      "전시"
    ],
    "tags": [
      "실내",
      "미디어아트",
      "새로운 시도",
      "잔잔한",
      "유쾌한",
      "공예",
      "조각",
      "체험형",
      "상상력",
      "야외"
    ]
  },
  "simulation_traits": {
    "monthly_culture_budget_krw": 90000,
    "price_sensitivity": "high",
    "culture_activity_frequency": "medium",
    "search_tendency": "low",
    "favorite_tendency": "high",
    "review_tendency": "medium",
    "purchase_tendency": "high",
    "companions": [
      "연인과"
    ],
    "personality": "이야기와 사회적 주제를 곱씹고 긴 후기를 남기는 편",
    "expected_behavior": "예산에 맞는 행사를 비교하고 결제는 신중하게 결정"
  }
}
```