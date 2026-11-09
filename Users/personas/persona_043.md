# 페르소나 작성 안내

테스트용 합성 사용자 데이터입니다. 가입 취향은 고정되며, 예산과 행동 성향은 시뮬레이션 판단에만 ```json
{
  "persona_id": "persona_043",
  "signup_profile": {
    "gender": "male",
    "age": 21,
    "region": "부산",
    "occupation": "마케팅 기획자",
    "mbti": "ISFJ",
    "cultural_categories": [
      "전시"
    ],
    "tags": [
      "일상 속 발견",
      "조각",
      "잔잔한",
      "가족",
      "설치미술",
      "몰입형",
      "활기찬",
      "인간관계",
      "미술관",
      "새로운 시도"
    ]
  },
  "simulation_traits": {
    "monthly_culture_budget_krw": 120000,
    "price_sensitivity": "low",
    "culture_activity_frequency": "high",
    "search_tendency": "low",
    "favorite_tendency": "medium",
    "review_tendency": "high",
    "purchase_tendency": "medium",
    "companions": [
      "연인과"
    ],
    "personality": "가격과 일정을 비교한 뒤 만족도가 높을 때 결제하는 편",
    "expected_behavior": "상세 페이지와 태그를 살펴본 뒤 비슷한 행사를 연이어 조회"
  }
}
```