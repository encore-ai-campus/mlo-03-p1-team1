# 페르소나 작성 안내

테스트용 합성 사용자 데이터입니다. 가입 취향은 고정되며, 예산과 행동 성향은 시뮬레이션 판단에만 ```json
{
  "persona_id": "persona_013",
  "signup_profile": {
    "gender": "male",
    "age": 31,
    "region": "경기",
    "occupation": "UX 리서처",
    "mbti": "ENFJ",
    "cultural_categories": [
      "전시"
    ],
    "tags": [
      "서예",
      "야외",
      "잔잔한",
      "참여형",
      "디자인",
      "미디어아트",
      "역사 이야기",
      "감동적인",
      "친구와",
      "입문자 친화"
    ]
  },
  "simulation_traits": {
    "monthly_culture_budget_krw": 250000,
    "price_sensitivity": "high",
    "culture_activity_frequency": "low",
    "search_tendency": "low",
    "favorite_tendency": "low",
    "review_tendency": "medium",
    "purchase_tendency": "medium",
    "companions": [
      "혼자 관람"
    ],
    "personality": "가격과 일정을 비교한 뒤 만족도가 높을 때 결제하는 편",
    "expected_behavior": "동행 가능한 날짜와 장소를 우선 확인하고 행사 선택"
  }
}
```