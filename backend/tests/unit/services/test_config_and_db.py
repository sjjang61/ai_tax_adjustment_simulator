import pytest
from pydantic import SecretStr

from app.core.config import ENV_FILE, ROOT_DIR, Settings
from app.db import MYSQL_POOL_RECYCLE_SECONDS, build_engine, engine_options

# 루트 .env 값의 영향을 받지 않도록 env 파일 없이 생성한다.
NO_ENV: dict[str, None] = {"_env_file": None}


def test_env_file_is_project_root() -> None:
    assert ENV_FILE == ROOT_DIR / ".env"
    assert (ROOT_DIR / "CLAUDE.md").exists()


def test_default_db_settings_are_local_mysql() -> None:
    s = Settings(**NO_ENV)  # type: ignore[arg-type]
    url = s.database_url
    assert url.get_backend_name() == "mysql"
    assert url.get_driver_name() == "pymysql"
    assert (url.host, url.port, url.database) == ("localhost", 3306, "tax_simulator")
    assert url.query["charset"] == "utf8mb4"
    assert url.password is None  # 비밀번호 미설정


def test_database_url_built_from_db_fields() -> None:
    s = Settings(
        _env_file=None,  # type: ignore[call-arg]
        db_host="db.local",
        db_port=3307,
        db_user="app",
        db_password=SecretStr("p@ss:w/rd#1"),
        db_name="tax_db",
    )
    url = s.database_url
    assert (url.host, url.port, url.username, url.database) == ("db.local", 3307, "app", "tax_db")
    assert url.password == "p@ss:w/rd#1"  # 특수문자 그대로 (URL 인코딩 불필요)
    rendered = url.render_as_string(hide_password=False)
    assert rendered.startswith("mysql+pymysql://app:p%40ss%3Aw%2Frd%231@db.local:3307/tax_db")
    assert "p@ss" not in str(url)  # 문자열 표현은 비밀번호를 가림
    assert "p@ss" not in repr(s)


def test_db_fields_read_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    env = {
        "DB_HOST": "127.0.0.1",
        "DB_PORT": "3310",
        "DB_USER": "env_user",
        "DB_PASSWORD": "secret",
        "DB_NAME": "env_db",
    }
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    s = Settings(**NO_ENV)  # type: ignore[arg-type]
    assert (s.db_host, s.db_port, s.db_user, s.db_name) == ("127.0.0.1", 3310, "env_user", "env_db")
    assert s.db_password.get_secret_value() == "secret"


def test_cors_origin_list() -> None:
    s = Settings(_env_file=None, cors_origins="http://a.test, http://b.test,")  # type: ignore[call-arg]
    assert s.cors_origin_list == ["http://a.test", "http://b.test"]


def test_mysql_engine_without_connecting() -> None:
    s = Settings(_env_file=None, app_env="local")  # type: ignore[call-arg]
    assert engine_options(s.database_url) == {
        "pool_pre_ping": True,
        "pool_recycle": MYSQL_POOL_RECYCLE_SECONDS,
    }
    engine = build_engine(s)
    assert engine.dialect.name == "mysql"
    assert engine.dialect.driver == "pymysql"
    engine.dispose()


def test_non_mysql_engine_options() -> None:
    from sqlalchemy import make_url

    assert engine_options(make_url("postgresql://u:p@h/db")) == {"pool_pre_ping": True}


def test_test_env_uses_in_memory_sqlite() -> None:
    engine = build_engine(Settings(_env_file=None, app_env="test"))  # type: ignore[call-arg]
    assert engine.dialect.name == "sqlite"
    engine.dispose()


def test_server_url_has_no_database() -> None:
    """DB 생성 스크립트는 DB를 지정하지 않고 서버에 접속해야 한다 (Unknown database 1049 방지)."""
    s = Settings(_env_file=None, db_name="tax_db", db_password=SecretStr("pw"))  # type: ignore[call-arg]
    url = s.server_url
    assert url.database is None
    assert (url.host, url.port, url.username, url.password) == (
        "localhost",
        3306,
        "tax_simulator",
        "pw",
    )
    assert url.query["charset"] == "utf8mb4"
    assert s.database_url.database == "tax_db"


def test_default_backend_port_is_8100() -> None:
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert (s.backend_host, s.backend_port) == ("127.0.0.1", 8100)
