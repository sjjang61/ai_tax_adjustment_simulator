"""애플리케이션 설정.

환경변수는 프로젝트 루트의 ``.env`` 하나만 사용한다. 실행 위치(cwd)에 의존하지 않도록 이 파일 기준
절대 경로로 지정한다: app/core/config.py → parents[3] = 프로젝트 루트.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL

BACKEND_DIR = Path(__file__).resolve().parents[2]
ROOT_DIR = Path(__file__).resolve().parents[3]
ENV_FILE = ROOT_DIR / ".env"

MYSQL_DRIVER = "mysql+pymysql"
MYSQL_CHARSET = "utf8mb4"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["local", "test", "production"] = "local"
    backend_host: str = "127.0.0.1"
    backend_port: int = 8100

    # MySQL 접속 정보 (.env의 DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME)
    db_host: str = "localhost"
    db_port: int = Field(default=3306, ge=1, le=65535)
    db_user: str = "tax_simulator"
    db_password: SecretStr = SecretStr("")
    db_name: str = "tax_simulator"

    # OpenAI (AI 추천). 키가 없으면 AI 추천 API는 503(ai_unavailable)을 반환한다.
    openai_api_key: SecretStr = SecretStr("")
    openai_model: str = "gpt-5.6-luna"
    openai_timeout_seconds: float = Field(default=60.0, gt=0, le=300)

    cors_origins: str = "http://localhost:5173"
    default_tax_year: int = 2025

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def _mysql_url(self, database: str | None) -> URL:
        """DB_* 값으로 MySQL 연결 URL을 만든다.

        URL.create가 계정·비밀번호의 특수문자를 처리하므로 .env에서 URL 인코딩할 필요가 없다.
        URL 객체의 문자열 표현은 비밀번호를 가린다(***).
        """
        password = self.db_password.get_secret_value()
        return URL.create(
            MYSQL_DRIVER,
            username=self.db_user,
            password=password or None,
            host=self.db_host,
            port=self.db_port,
            database=database,
            query={"charset": MYSQL_CHARSET},
        )

    @property
    def database_url(self) -> URL:
        """앱이 사용하는 DB(DB_NAME) 연결 URL."""
        return self._mysql_url(self.db_name)

    @property
    def server_url(self) -> URL:
        """DB를 지정하지 않은 서버 연결 URL (DB 생성용).

        주의: URL.set(database=None)은 None을 "변경 없음"으로 처리해 DB가 남으므로 새로 만든다.
        """
        return self._mysql_url(None)


@lru_cache
def get_settings() -> Settings:
    return Settings()
