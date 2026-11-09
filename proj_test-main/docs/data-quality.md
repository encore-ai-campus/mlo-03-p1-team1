# 수집과 데이터 품질

문화포털 ‘한눈에보는문화정보 조회서비스’의 period와 detail을 사용한다. [공식 사용 가이드](https://www.culture.go.kr/portal/main/contents.do?menuNo=200155) 기준 base URL은 `https://apis.data.go.kr/B553457/nopenapi/rest/publicperformancedisplays`. 서비스 키 발급/승인과 할당량은 사용자가 설정한다.

`backend/app/collectors`는 HTTP/XML 수집, `backend/app/pipelines`는 HTML 텍스트화·날짜·가격·URL·분야·지역 정규화, `backend/app/tasks/collect.py`는 트랜잭션 저장과 반복 실행을 담당한다. 목록 최대 pages×100건, 레코드별 상세 조회. `(source, source_id)`로 기존 항목 갱신. 날짜/제목/ID 불량 건은 건너뛰고 공급자 오류는 배치 롤백한다. 키가 포함된 요청 URL이나 XML 원문을 로그에 남기지 않는다.

보안 XML 파서(defusedxml), 20초 HTTP timeout, 응답 5MB 크기 검사, 허용 http(s) 링크만 저장. API 응답의 가격 문자열은 내부 판매가로 추정하지 않는다. 정확히 무료/전석 무료/0원인 경우만 무료 필터에 포함한다. 알려지지 않은 금액은 ‘주최 기관 확인’, 내부 price=0, bookable=false다.

기본 검색·추천은 종료된 행사 제외(KST 현재 날짜). 여러 공급자 사이의 동일 행사 병합과 취소 공지 판별은 아직 없다. 공급자가 누락시킨 정보는 자동 삭제하지 않아 일시 장애로 콘텐츠가 사라지는 것을 방지한다. 상세 페이지에서 수집일/출처와 최종 일정 확인 안내를 제공한다.

샘플 12개와 SVG 포스터는 자체 제작한 가상 데이터다. 실제 행사·장소·일정으로 사용하면 안 되며 샘플 배지와 내부 결제 금지를 적용한다. 실제 수집 키가 준비되면 `backend` 폴더에서 `python -m app.tasks.collect`로 실제 정보를 수집한다. 샘플 제거는 관리자가 `source='sample'`인 콘텐츠를 검토 후 삭제한다. 운영 API에 임의 삭제 엔드포인트는 노출하지 않는다.

운영 도입 전 제공처의 이용 허락·출처 표시·이미지 사용 조건을 확인해야 한다. 데이터/활동 보존·삭제 정책은 팀에서 확정한다.
