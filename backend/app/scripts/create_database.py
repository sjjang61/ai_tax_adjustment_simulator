"""MySQL 데이터베이스(.env의 DB_NAME)가 없으면 utf8mb4로 생성한다 (테이블은 앱 시작 시 자동 생성).

사용: uv run python -m app.scripts.create_database
.env의 DB_USER 계정에 CREATE 권한이 있어야 한다.
"""

from sqlalchemy import create_engine, text

from app.core.config import get_settings
from app.db import engine_options


def main() -> None:
    settings = get_settings()
    server_url = settings.server_url
    engine = create_engine(server_url, **engine_options(server_url))
    with engine.begin() as conn:
        quoted = conn.dialect.identifier_preparer.quote(settings.db_name)
        conn.execute(
            text(
                f"CREATE DATABASE IF NOT EXISTS {quoted} "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        )
    engine.dispose()
    print(f"데이터베이스 준비 완료: {settings.db_name} ({settings.db_host}:{settings.db_port})")


if __name__ == "__main__":
    main()
