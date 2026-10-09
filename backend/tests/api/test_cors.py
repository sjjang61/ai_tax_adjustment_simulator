"""CORS 프리플라이트: local은 localhost 임의 포트 허용, production은 CORS_ORIGINS만 허용."""

from typing import Literal

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def _preflight(app_env: Literal["local", "production"], origin: str) -> int:
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        app_env=app_env,
        cors_origins="http://localhost:5173",
    )
    app = create_app(settings)
    # 앱 시작(lifespan)으로 실제 DB에 연결하지 않도록 컨텍스트 없이 요청만 보낸다.
    client = TestClient(app)
    res = client.options(
        "/api/v1/rules", headers={"Origin": origin, "Access-Control-Request-Method": "GET"}
    )
    return res.status_code


@pytest.mark.parametrize(
    "origin",
    [
        "http://localhost:5173",
        "http://localhost:5174",  # 5173 사용 중일 때 Vite가 자동으로 고른 포트
        "http://127.0.0.1:5173",
        "http://127.0.0.1:4173",  # vite preview
    ],
)
def test_local_allows_any_localhost_port(origin: str) -> None:
    assert _preflight("local", origin) == 200


@pytest.mark.parametrize(
    "origin",
    ["http://evil.test", "http://localhost.evil.test:5173", "https://localhost:5173.evil.test"],
)
def test_local_still_rejects_other_hosts(origin: str) -> None:
    assert _preflight("local", origin) == 400


def test_production_allows_only_configured_origins() -> None:
    assert _preflight("production", "http://localhost:5173") == 200
    assert _preflight("production", "http://localhost:5174") == 400
