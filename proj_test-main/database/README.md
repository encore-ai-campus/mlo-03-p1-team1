# 데이터베이스

MariaDB만 사용한다. 행동 이벤트도 MariaDB에 보관하며 MongoDB는 팀 합의 전 도입하지 않는다.

- 스키마 적용: backend에서 `alembic upgrade head`.
- `mariadb/schema.sql`은 migration에서 내보낸 참고용 DDL. 직접 적용하지 않는다.
- DB/계정 생성·권한: `mariadb/permissions.sql`의 플레이스홀더를 DBA가 수정해 실행한다.
- 앱 계정 DML, 마이그레이션 계정 DDL, 수집 계정 contents DML을 분리한다.
- `backend` 폴더에서 실행하는 `python -m app.tasks.seed`는 샘플 콘텐츠만 추가하며 실제 계정/비밀번호를 만들지 않는다.
- `backup/` 안의 덤프는 Git에서 제외한다. 운영 백업은 별도 암호화 저장소와 복구 훈련이 필요하다.
- 추가 설정은 [환경 구성](../docs/setup.md) 참조.
