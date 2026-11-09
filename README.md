## 1. 팀 소개

**팀명: PrefIO**

| 고은빈 | 박완규 | 진세은 |
|---|---|---|
| <img src="https://github.com/user-attachments/assets/8d8ff4bb-88b7-4c3d-a6a9-c049e434b698" width="100"> | <img src="https://avatars.githubusercontent.com/u/148618067?v=4" width="100"> | <img src="https://github.com/user-attachments/assets/709cca20-b9cb-4a35-b704-84ffff9b6064" width="100"> |
| [@Eunbinko](https://github.com/eunbinko) | [@domomo](https://github.com/domomo) | [@wlstpdms](https://github.com/wlstpdms) |

  <br />
  
## 2. 프로젝트 개요

### 2.1 프로젝트명

**Oddinary : 오디너리**

Odd(특별한, 독특한)*와 *Ordinary(평범한)*를 결합한 이름으로, 평범한 일상 속에서 자신만의 특별한 문화 경험을 발견



### 2.2 프로젝트 소개

Oddinary는 사용자 프로필 정보와 서비스 내 활동 데이터를 수집하여 개인의 취향에 맞는 문화 콘텐츠를 추천하는 데이터 기반 웹 서비스입니다.

Open API(문화체육관광부)와 네이버 크롤링으로 문화 컨텐츠 정보를 수집하고, 사용자 취향에 맞는 콘텐츠를 추천하는 데이터 기반 서비스입니다.

회원 관리, 문화 컨텐츠 정보 조회 및 검색, 맞춤형 추천, 모의 결제 기능을 제공하고, 사용자 활동 데이터를 활용하여 개인화 추천 기능을 구현하였습니다.



### 2.3 프로젝트 필요성 및 배경

문화 생활은 사용자의 지역, 나이, 관심도, 성향 등 설정한 프로필에 따라 다양한 선호도가 생길 수 있습니다. 서비스 내에서 사용자들의 선호도에 따른 사용자들의 활동 데이터를 수집하고 이를 분석하여 개인에게 적합한 컨텐츠 추천하는 과정이 필요합니다.

검색 - 상세 페이지 조회 - 찜 - 결제에서 발생하는 사용자 데이터가 한 흐름에만 국한되지 않고 프로필에 따라 여러 사용 흐름을 만들어내 데이터 분석에 적합한 컨텐츠라고 판단하였습니다.



### 2.4 프로젝트 목표

기능 구현: 회원 관리, 문화 컨텐츠 조회, 검색, 찜/리뷰, 맞춤형 추천 페이지, 모의 결제 기능을 갖춘 웹 서비스 구현

데이터 수집: 외부 Open API를 통한 문화 콘텐츠 정보와 서비스 이용 과정에서 발생하는 사용자 행동 데이터 수집

데이터 저장 및 처리: 수집한 데이터를 정제하고 데이터베이스에 저장

데이터 활용: 사용자 취향 및 활동 데이터를 기반으로 맞춤형 콘텐츠를 추천하고, 추후에 이용 패턴 분석에 활용


   <br />
   
## 3. 기술 스택

<img src="https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/react/react-original.svg" width="60" alt="React"> <img src="https://images.openai.com/static-rsc-4/rACPM-tH7pnaqEZHZVHA5PkkgCszQHcz2ydzFwZZpu9zS92TaNbZCfXKixb7QheTuD1uma7qpIBGFK-lsL3ODTHlqyv1PRgnpZPBLneYa5W23YxS1dHW5dET_VQ_k3AA0ZEdYbXlAdpI7QUTGnjNWvuxt1MEy9WmYKkT5mWKhcinaO5HK5Jng93bolaWogMk?purpose=fullsize" width="100"><img src="https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/fastapi/fastapi-original.svg" width="60" alt="FastAPI"> <img src="https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/nginx/nginx-original.svg" width="60" alt="Nginx"> <img src="https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/mariadb/mariadb-original.svg" width="60" alt="MariaDB"><img src="https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/mongodb/mongodb-original.svg" width="60" alt="MongoDB"><img src="https://raw.githubusercontent.com/grafana/alloy/main/docs/sources/assets/logo_alloy_dark.svg" height="60" alt="Grafana Alloy"><img src="https://grafana.com/docs/loki/latest/logo_and_name.png" height="60" alt="Grafana Loki"><img src="https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/prometheus/prometheus-original.svg" width="60" alt="Prometheus"><img src="https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/grafana/grafana-original.svg" width="60" alt="Grafana">
 
   <br />
   
## 4. WBS

현재 코드에 구현된 기능을 기준으로 정리한 작업 분류표입니다. 작업 코드는 기능별로 구분합니다.

| 작업 코드 | 작업 항목 | 담당자 |
| --- | --- | --- |
| PROJ-01 | 프로젝트 주제 선정 및 주요 기능 정의 | 전원 |
| MEM-01 | 회원 인증·프로필·취향 설문 API 구현 | 박완규 |
| MEM-02 | 회원 인증·마이페이지·취향 설문 화면 구현 | 진세은 |
| CONT-01 | 문화 콘텐츠 검색·조회 API 구현 | 박완규 |
| CONT-02 | 문화 콘텐츠 탐색·상세 화면 구현 | 진세은 |
| ACT-01 | 찜·리뷰·조회 이력 및 행동 기록 API 구현 | 박완규 |
| ACT-02 | 찜·리뷰·최근 조회 화면 구현 | 진세은 |
| RECO-01 | 사용자 취향·활동 기반 추천 로직 구현 | 박완규 |
| RECO-02 | 홈 및 맞춤 추천 화면 구현 | 진세은 |
| PAY-01 | 주문 생성 로직 및 결제 내역 조회 구현 | 박완규 |
| PAY-02 | 주문 정보·이용 내역 화면 구현 | 진세은 |
| DATA-01 | DB 설계·구축 및 스키마 관리 | 고은빈 |
| DATA-02 | 문화 콘텐츠 수집·정제 및 데이터 구성 | 고은빈 |

 <br />
 
## 5. 요구사항 명세서
[요구사항 명세서 이슈 상세보기](https://github.com/encore-ai-campus/mlo-03-p1-team1/issues/31)

## 6. 시스템 설계

### 6.1 시스템 아키텍처
[시스템 아키텍처 WIKI 상세보기](https://github.com/encore-ai-campus/mlo-03-p1-team1/wiki/System%E2%80%90Architecture)
 
<img width="3578" height="2188" alt="SystemArchitecture" src="https://github.com/user-attachments/assets/530fb772-7282-4c2b-9db7-f9d11290df06" />

### 6.2 ERD (Entity Relationship Diagram)
 [ERD WIKI 상세보기](https://github.com/encore-ai-campus/mlo-03-p1-team1/wiki/ERD)
 
 <img width="3578" height="2188" alt="SystemArchitecture" src="https://github.com/user-attachments/assets/d57ebe33-b78b-470b-9194-f9500e460855" />

 
## 7. 주요 프로시저 

### 7.1 개요 [주요 프로시저 WIKI 상세보기](https://github.com/encore-ai-campus/mlo-03-p1-team1/wiki/%EC%A3%BC%EC%9A%94-%ED%94%84%EB%A1%9C%EC%8B%9C%EC%A0%80)
데이터베이스에서 반복적으로 수행되는 주요 SQL 작업 관리


<img width="1672" height="941" alt="주요 프로시저 데이터 흐름도" src="https://github.com/user-attachments/assets/185f2f52-f1ce-4fd9-a806-2635f002a07b" />

## 8. 활용 데이터

| 구분 | 데이터 출처 | 수집 방식 | 수집 범위 |
|---|---|---|---|
| 공공 데이터 | 문화체육관광부 문화공공데이터광장 — 문화예술공연(통합) API | API 호출 후 DB 저장 | API에서 제공하는 문화예술공연 정보 |
| 웹 수집 데이터 | 네이버 | 키워드 기반 크롤링 | 전시, 뮤지컬, 연극, 콘서트, 클래식, 가족/아동, 뮤직페스티벌, 공연제 |
 <br />

## 9. 수행결과 (테스트/시연 페이지)
 
## 10. 팀원별 한 줄 회고

| 팀원 | 한 줄 회고 |
|---|---|
| 고은빈 | |
| 박완규 | |
| 진세은 | |
