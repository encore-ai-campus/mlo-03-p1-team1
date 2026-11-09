# Oddinary Persona Simulator

100개의 합성 페르소나 중 하나를 골라 Oddinary 사이트의 실제 브라우저 UI에서 탐색하는 비동기 Playwright 시뮬레이터입니다. 프론트엔드 UI만 조작하며 MongoDB에 직접 연결하거나 이벤트를 중복 전송하지 않습니다.

## 실행

Python 3.10 이상에서 프로젝트 폴더에 설치합니다.

```bash
python -m pip install -r requirements.txt
python -m playwright install chromium
```

최초 실행 시 100개 페르소나의 무작위 로그인 이메일과 비밀번호가 `runs/test_accounts.json`에 한 번 생성됩니다. 이미 존재하는 계정의 비밀번호는 재생성하지 않습니다. 가입 성공 시 이 파일에 `registered: true`가 기록되어 다음 실행부터 로그인으로 바로 들어갑니다. 이 파일은 `.gitignore`에 포함되어 저장소에 커밋되지 않습니다. `ODDINARY_TEST_EMAIL_DOMAIN`으로 가입 가능한 테스트용 이메일 도메인을 지정할 수 있습니다. 기본 도메인은 사이트 도메인인 `aiready.p-e.kr`입니다. 이전에 만든 `example.test` 주소는 가입 API에서 거부되어 로컬 부분과 비밀번호를 유지한 채 기본 도메인으로 교체합니다.

PowerShell:

```powershell
$env:ODDINARY_TEST_EMAIL_DOMAIN = '검증된-테스트-메일-도메인'
python -m src.main persona_001.md
```

Bash/Ubuntu:

```bash
export ODDINARY_TEST_EMAIL_DOMAIN='검증된-테스트-메일-도메인'
python -m src.main persona_001.md
```

실제 가입 허용 도메인 또는 메일 인증이 필요한 경우 서비스 운영 환경에서 사용할 테스트 전용 도메인을 지정한 후 `runs/test_accounts.json`을 생성하세요. 사이트가 가입 폼에 약관 동의를 표시하면 프로그램은 최종 가입 직전에 터미널에서 실행자의 확인을 받습니다.

Ubuntu 서버에서 화면이 없으면 headless Chromium으로 자동 실행합니다. 설정은 `ODDINARY_HEADLESS=1` 또는 `ODDINARY_HEADLESS=0`으로 덮어쓸 수 있습니다. Playwright가 설치한 Chromium이 없다면 설치 명령을 먼저 실행하세요.

페르소나 파일명 하나만 인자로 받으며 실제 파일은 `personas/`에서 읽습니다. 확률은 Codex CLI가 있으면 JSON Schema를 지정한 `codex exec`로 생성하고, CLI가 없거나 실행에 실패하면 `config/behavior_rules.json`의 기본값과 페르소나 행동 성향을 이용하는 Python 로직으로 생성합니다.

## 설정과 결과

- `config/behavior_rules.json`: 기본 행동 확률, 성향별 계수, 관심/발견 카테고리 가중치, 검색어, 행동 간 대기와 세션 한도를 관리합니다.
- `config/behavior_output.schema.json`: Codex 행동·카테고리 확률 결과의 형식을 제한합니다.
- `src/persona_loader.py`: Markdown JSON 블록, 고정 프로필, 카테고리 및 표준 태그를 확인합니다.
- `src/codex_runner.py`: Codex 또는 Python 대체 확률 생성, 확률 분포 검증을 합니다.
- `src/simulator.py`: 실제 웹 UI의 보이는 링크·버튼·입력란만 사용합니다.
- `runs/<persona_id>_behavior.json`: 생성 확률.
- `runs/<persona_id>_simulation.json`: 시간순 행동, 성공/건너뜀/실패와 이유, 확인한 콘텐츠 ID·카테고리·태그, 조회 순서 및 요약.
- `runs/test_accounts.json`: 100명분의 무작위 테스트 로그인 ID·비밀번호. 저장소에 커밋하지 않습니다.

## 확인된 범위와 제한

사이트 첫 화면의 로컬 취향 설정 창은 닫고 헤더의 로그인 창에서 회원가입으로 전환합니다. 확인한 가입 화면은 이름·이메일·비밀번호로 시작하고, 프로필 및 취향 단계를 이어가는 3단계 흐름입니다. 가입에 필요한 실제 프로필 필드는 실행 중 현재 화면의 라벨과 입력 종류를 확인해 입력합니다. 페르소나에 이름 필드가 없어서 테스트용 이름을 생성하며, 비밀번호는 `runs/test_accounts.json`에서만 읽습니다. 이미 존재하는 이메일은 로그인으로 전환합니다. 로그인 성공을 확인하기 전에는 콘텐츠 동작을 시작하지 않습니다. 상세 화면의 결제와 리뷰 입력은 로그인 후 화면에서 동작이 확인되지 않아 제출하지 않습니다.

저장소에는 프론트엔드와 FastAPI 이벤트 수집 구현이 포함되어 있지 않아 MongoDB 이벤트가 실제로 수집되는지는 이 저장소만으로 검증할 수 없습니다. 브라우저에서 사이트 UI를 이용할 때 사이트 자체 이벤트 흐름이 실행되며 시뮬레이터는 같은 이벤트를 별도로 전송하지 않습니다. 현재 화면에서 노출되지 않는 기능은 임의의 경로나 API를 만들지 않고 결과 JSON에 건너뜀/실패 사유를 남깁니다.
