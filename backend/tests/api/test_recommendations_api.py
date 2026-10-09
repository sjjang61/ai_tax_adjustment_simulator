from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.api.v1.recommendations import get_recommendation_client
from app.core.config import Settings
from app.main import create_app
from app.schemas.recommendation import LlmAdjustment, LlmOutput, LlmRecommendation
from tests.factories import input_dict

URL = "/api/v1/recommendations"


class FakeClient:
    def generate(self, *, instructions: str, payload: str, output_type: type[Any]) -> Any:
        return LlmOutput(
            summary="연금계좌 한도가 남아 있습니다.",
            recommendations=[
                LlmRecommendation(
                    title="IRP 추가 납입",
                    category="tax_credit",  # type: ignore[arg-type]
                    reason="연금계좌 합산 한도 여유",
                    action="연말 전 IRP에 납입",
                    adjustment=LlmAdjustment(field="credits.irp", additional_amount=3_000_000),
                )
            ],
        )


def _app(api_key: str = "") -> TestClient:
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        app_env="test",
        openai_api_key=SecretStr(api_key),
    )
    return TestClient(create_app(settings))


@pytest.fixture
def client_with_fake() -> Iterator[TestClient]:
    client = _app("sk-test")
    client.app.dependency_overrides[get_recommendation_client] = FakeClient  # type: ignore[attr-defined]
    with client as c:
        yield c


def test_unavailable_without_api_key() -> None:
    with _app("") as c:
        res = c.post(URL, json=input_dict())
    assert res.status_code == 503
    assert res.json()["code"] == "ai_unavailable"


def test_recommendations_with_engine_savings(client_with_fake: TestClient) -> None:
    res = client_with_fake.post(URL, json=input_dict(income={"annual_earned_income": 50_000_000}))
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["model"] == "gpt-5.6-luna"
    rec = body["recommendations"][0]
    assert rec["estimated_saving"] > 0
    assert rec["adjusted_input"]["credits"]["irp"] == 3_000_000
    assert body["disclaimer"]


def test_validation_error(client_with_fake: TestClient) -> None:
    res = client_with_fake.post(URL, json=input_dict(unknown=1))
    assert res.status_code == 422
