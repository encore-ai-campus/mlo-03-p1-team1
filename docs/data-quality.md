# 수집과 데이터 품질

문화포털 ‘한눈에보는문화정보 조회서비스’의 period와 detail을 사용한다. [공식 사용 가이드](https://www.culture.go.kr/portal/main/contents.do?menuNo=200155) 기준 base URL은 `https://apis.data.go.kr/B553457/nopenapi/rest/publicperformancedisplays`. 서비스 키 발급/승인과 할당량은 사용자가 설정한다.

`backend/app/collectors`는 HTTP/XML 수집, `backend/app/pipelines`는 HTML 텍스트화·날짜·가격·URL·분야·지역 정규화, `backend/app/tasks/collect.py`는 트랜잭션 저장과 반복 실행을 담당한다. 목록 최대 pages×100건, 레코드별 상세 조회. `(source, source_id)`로 기존 항목 갱신. 날짜/제목/ID 불량 건은 건너뛰고 공급자 오류는 배치 롤백한다. 키가 포함된 요청 URL이나 XML 원문을 로그에 남기지 않는다.

보안 XML 파서(defusedxml), 20초 HTTP timeout, 응답 5MB 크기 검사, 허용 http(s) 링크만 저장. API 응답의 가격 문자열은 내부 판매가로 추정하지 않는다. 정확히 무료/전석 무료/0원인 경우만 무료 필터에 포함한다. 알려지지 않은 금액은 ‘주최 기관 확인’, 내부 price=0, bookable=false다.

기본 검색·추천은 종료된 행사 제외(KST 현재 날짜). 여러 공급자 사이의 동일 행사 병합과 취소 공지 판별은 아직 없다. 공급자가 누락시킨 정보는 자동 삭제하지 않아 일시 장애로 콘텐츠가 사라지는 것을 방지한다. 상세 페이지에서 수집일/출처와 최종 일정 확인 안내를 제공한다.

샘플 12개와 SVG 포스터는 자체 제작한 가상 데이터다. 실제 행사·장소·일정으로 사용하면 안 되며 샘플 배지와 내부 결제 금지를 적용한다. 실제 수집 키가 준비되면 `backend` 폴더에서 `python -m app.tasks.collect`로 실제 정보를 수집한다. 샘플 제거는 관리자가 `source='sample'`인 콘텐츠를 검토 후 삭제한다. 운영 API에 임의 삭제 엔드포인트는 노출하지 않는다.

운영 도입 전 제공처의 이용 허락·출처 표시·이미지 사용 조건을 확인해야 한다. 데이터/활동 보존·삭제 정책은 팀에서 확정한다.

## 네이버 전시 CSV 적재

기존 `backend/app/tasks/`의 `import_naver.py`로 CSV를 적재한다. 기존 테이블·프론트엔드 경로는 변경하지 않는다. `backend/.env`의 `DATABASE_URL`에 지정된 DB를 사용하며, 현재 대상은 VM master의 `culture` DB다.

가상환경을 활성화한 뒤 `backend` 폴더에서 실행한다.

```powershell
cd backend
python -m app.tasks.import_naver C:/Users/Playdata/Downloads/naver_exhibitions_2026-11-04_enriched_partial.csv --dry-run
# 확인 후 실제 적재
python -m app.tasks.import_naver C:/Users/Playdata/Downloads/naver_exhibitions_2026-11-04_enriched_partial.csv
```

- CSV의 `전시중`은 행사 상태이므로 서비스 분야 `전시`로 변환한다. 도로명 주소가 있는 경우에만 지역을 정규화하고, 지역·가격 미제공 항목은 확인 필요로 표시한다. 판매 가격은 추정하지 않으며 신규 항목은 `bookable=false`, `is_sample=false`로 저장한다.
- 날짜가 없는 행과 유효하지 않은 날짜 범위는 적재하지 않는다. 날짜를 임의 생성하거나 테이블의 필수 조건을 변경하지 않는다. 제외 사유와 CSV 원본 행은 Git 제외 파일 `.runtime/naver-import-report.json`에 보관한다.
- `poster_source_url` 이미지를 기존 `frontend/public/posters/naver-<식별자>.<확장자>`로 다운로드하고 DB의 `image_url`에는 `/posters/...`를 저장한다. CSV의 다른 PC용 `poster_local_path`는 사용하지 않는다. 이미지 시그니처·크기를 확인하고 다운로드 오류는 재시도하며, 끝내 실패하면 DB 적재는 진행하지 않는다. URL이 없는 항목에는 기존 대체 포스터를 사용한다.
- `(source='naver_exhibitions', source_id)`로 중복을 방지한다. 식별자는 제목·장소·지도 장소 ID로 생성하므로 CSV 순번 변경으로 중복 생성되지 않는다. 재실행 시 기존 콘텐츠 ID·찜·리뷰와 별도로 설정한 판매 가능 여부·가격을 유지한다. 다운로드된 이미지는 재사용하고 DB 저장은 한 트랜잭션으로 처리한다.
- 2026-11-04 CSV는 총 540행이며 날짜가 있는 479행을 적재했다. 나머지 61행은 날짜가 없어 제외했다. 이미지 URL이 있는 528개를 다운로드했으며, URL이 없는 12개는 대체 이미지 대상으로 기록했다. 이 중 실제 적재된 콘텐츠의 대체 이미지 사용은 1건이다. 2026-11-05 기준 기본 목록에는 종료된 5건을 제외한 474건이 표시된다.

프론트엔드 빌드 시 다운로드한 이미지도 `frontend/dist/posters/`에 포함된다. 다른 PC나 배포 서버에서도 이미지를 제공하려면 이 정적 파일을 함께 전달해야 한다.
