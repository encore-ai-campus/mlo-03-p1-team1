# 데이터베이스

MariaDB는 업무 상태와 behavior_events/outbox를 관리한다. 2026-11-06 사용자 요청으로 MongoDB `oddinary.user_events`에 분석 이벤트를 적재하도록 도입했다. 업무와 이벤트의 동일 트랜잭션 및 전달 멱등성을 보장하며, MongoDB의 이벤트가 찜/주문/결제 상태를 대체하지 않는다. [MongoDB 스키마·실측 결과](mongodb/README.md), [이벤트 계약](../docs/event-contract.md) 참조.

- 스키마 적용: backend에서 `alembic upgrade head`.
- `mariadb/schema.sql`은 migration에서 내보낸 참고용 DDL. 직접 적용하지 않는다.
- DB/계정 생성·권한: `mariadb/permissions.sql`의 플레이스홀더를 DBA가 수정해 실행한다.
- 앱 계정 DML, 마이그레이션 계정 DDL, 수집 계정 contents DML을 분리한다.
- `backend` 폴더에서 실행하는 `python -m app.tasks.seed`는 샘플 콘텐츠만 추가하며 실제 계정/비밀번호를 만들지 않는다.
- `backup/` 안의 덤프는 Git에서 제외한다. 운영 백업은 별도 암호화 저장소와 복구 훈련이 필요하다.
- 추가 설정은 [환경 구성](../docs/setup.md) 참조.
