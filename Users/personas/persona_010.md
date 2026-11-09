# 페르소나 작성 안내

테스트용 합성 사용자 데이터입니다. 가입 취향은 고정되며, 예산과 행동 성향은 시뮬레이션 판단에만 ```json
{
  "persona_id": "persona_010",
  "signup_profile": {
    "gender": "female",
    "age": 32,
    "region": "충북",
    "occupation": "건축 설계사",
    "mbti": "ESFJ",
    "cultural_categories": [
      "음악"
    ],
    "tags": [
      "사진 남기기",
      "합창",
      "실내",
      "대극장",
      "일상 속 발견",
      "이야기",
      "아이와",
      "해설과 함께",
      "힙합",
      "크로스오버"
    ]
  },
  "simulation_traits": {
    "monthly_culture_budget_krw": 120000,
    "price_sensitivity": "medium",
    "culture_activity_frequency": "high",
    "search_tendency": "high",
    "favorite_tendency": "high",
    "review_tendency": "low",
    "purchase_tendency": "medium",
    "companions": [
      "가족"
    ],
    "personality": "사람들과 함께 즐기고 생생한 현장 분위기를 좋아하는 편",
    "expected_behavior": "예산에 맞는 행사를 비교하고 결제는 신중하게 결정"
  }
}
```