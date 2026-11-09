# 페르소나 작성 안내

테스트용 합성 사용자 데이터입니다. 가입 취향은 고정되며, 예산과 행동 성향은 시뮬레이션 판단에만 ```json
{
  "persona_id": "persona_090",
  "signup_profile": {
    "gender": "female",
    "age": 41,
    "region": "인천",
    "occupation": "건축 설계사",
    "mbti": "ENFJ",
    "cultural_categories": [
      "축제"
    ],
    "tags": [
      "인간관계",
      "참여형",
      "유쾌한",
      "친구와",
      "음악페스티벌",
      "입문자 친화",
      "웅장한",
      "독립공간",
      "미술관",
      "영화제"
    ]
  },
  "simulation_traits": {
    "monthly_culture_budget_krw": 40000,
    "price_sensitivity": "medium",
    "culture_activity_frequency": "low",
    "search_tendency": "low",
    "favorite_tendency": "low",
    "review_tendency": "medium",
    "purchase_tendency": "low",
    "companions": [
      "혼자 관람"
    ],
    "personality": "차분히 관찰하고 작품의 맥락을 찾아보는 편",
    "expected_behavior": "예산에 맞는 행사를 비교하고 결제는 신중하게 결정"
  }
}
```