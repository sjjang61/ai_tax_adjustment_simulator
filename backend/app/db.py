"""DB 엔진·세션 구성.

- 기본(local/production): MySQL (``mysql+pymysql://``, utf8mb4), 접속 정보는 .env의 DB_* 값
- 테스트(APP_ENV=test): 인메모리 SQLite
"""

from collections.abc import Iterator
from typing import Any

from fastapi import Request
from sqlalchemy import URL, Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.models.base import Base

# MySQL 서버의 wait_timeout(기본 8시간)보다 짧게 연결을 재생성한다.
MYSQL_POOL_RECYCLE_SECONDS = 3600


def engine_options(url: URL) -> dict[str, Any]:
    """드라이버별 create_engine 옵션."""
    if url.get_backend_name() == "mysql":
        # 끊긴 연결을 사용 전에 감지하고, 서버 타임아웃 전에 재생성한다.
        return {"pool_pre_ping": True, "pool_recycle": MYSQL_POOL_RECYCLE_SECONDS}
    return {"pool_pre_ping": True}


def _enable_sqlite_foreign_keys(engine: Engine) -> None:
    """SQLite는 기본적으로 외래키(ON DELETE SET NULL 등)를 강제하지 않으므로 연결마다 켠다."""

    @event.listens_for(engine, "connect")
    def _on_connect(dbapi_connection: Any, _record: Any) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def build_engine(settings: Settings) -> Engine:
    if settings.app_env == "test":
        # 테스트: 인메모리 SQLite, 모든 연결이 같은 DB를 공유하도록 StaticPool 사용
        engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        _enable_sqlite_foreign_keys(engine)
        return engine
    url = settings.database_url
    return create_engine(url, **engine_options(url))


def init_db(engine: Engine) -> None:
    import app.models.global_income
    import app.models.simulation  # noqa: F401

    Base.metadata.create_all(engine)


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session(request: Request) -> Iterator[Session]:
    factory: sessionmaker[Session] = request.app.state.session_factory
    with factory() as session:
        yield session
