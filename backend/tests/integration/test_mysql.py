"""실제 MySQL 서버 통합 테스트 (선택 실행).

전용 테스트 DB 이름을 MYSQL_TEST_DB_NAME 환경변수로 지정했을 때만 실행한다. 접속 정보(DB_HOST,
DB_PORT, DB_USER, DB_PASSWORD)는 루트 .env 값을 사용한다. 테이블을 만들고 지우므로 개발·운영 DB
이름(DB_NAME)과 같으면 실행을 거부한다. 테스트 DB는 미리 만들어 두어야 한다.

    MYSQL_TEST_DB_NAME=tax_simulator_test uv run pytest tests/integration -q
"""

import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.models.base import Base
from tests.factories import input_dict

MYSQL_TEST_DB_NAME = os.environ.get("MYSQL_TEST_DB_NAME")

pytestmark = pytest.mark.skipif(not MYSQL_TEST_DB_NAME, reason="MYSQL_TEST_DB_NAME 미설정")


@pytest.fixture
def mysql_client() -> Iterator[TestClient]:
    assert MYSQL_TEST_DB_NAME
    base = Settings(app_env="local")
    if base.db_name == MYSQL_TEST_DB_NAME:
        pytest.fail("MYSQL_TEST_DB_NAME이 DB_NAME과 같습니다. 전용 테스트 DB를 지정하세요.")
    settings = base.model_copy(update={"db_name": MYSQL_TEST_DB_NAME})
    app = create_app(settings)
    with TestClient(app) as client:
        yield client
    engine = app.state.session_factory.kw["bind"]
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_crud_and_carry_over_on_mysql(mysql_client: TestClient) -> None:
    api = "/api/v1"
    created = mysql_client.post(
        f"{api}/simulations",
        json={"name": "한글 이름 테스트 🧾", "input": input_dict()},
    ).json()
    assert created["name"] == "한글 이름 테스트 🧾"  # utf8mb4
    assert created["created_at"].endswith(("+00:00", "Z"))

    got = mysql_client.get(f"{api}/simulations/{created['id']}").json()
    assert got["input"] == created["input"]
    assert got["result"]["determined_tax"] == created["determined_tax"]

    carried = mysql_client.post(
        f"{api}/simulations/{created['id']}/carry-over", params={"target_year": 2026}
    ).json()
    assert carried["simulation"]["source_simulation_id"] == created["id"]

    # 원본 삭제 시 초안의 source_simulation_id는 NULL (ON DELETE SET NULL)
    assert mysql_client.delete(f"{api}/simulations/{created['id']}").status_code == 204
    draft = mysql_client.get(f"{api}/simulations/{carried['simulation']['id']}").json()
    assert draft["source_simulation_id"] is None
