from typing import Any

from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.api.v1.recommendations import get_recommendation_client
from app.core.config import Settings
from app.main import create_app
from app.services.ai_couple import LlmCoupleOutput, LlmDependentReason
from tests.factories import input_dict

BODY = {
    "tax_year": 2025,
    "primary": input_dict(
        income={"annual_earned_income": 80_000_000}, taxpayer={"is_married": True}
    ),
    "spouse": input_dict(
        income={"annual_earned_income": 40_000_000}, taxpayer={"is_married": True}
    ),
    "shared_dependents": [
        {"relation": "lineal_ascendant", "birth_year": 1966, "medical_expense": 3_000_000}
    ],
}


def _client(api_key: str = "") -> TestClient:
    return TestClient(
        create_app(
            Settings(_env_file=None, app_env="test", openai_api_key=SecretStr(api_key))  # type: ignore[call-arg]
        )
    )


def test_optimize() -> None:
    with _client() as c:
        res = c.post("/api/v1/couples/optimize", json=BODY)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["best"]["assignment"] == ["spouse"]
    assert body["baseline"]["assignment"] == ["primary"]
    assert body["saving"] > 0
    assert body["evaluated_count"] == 2
    assert body["best_spouse_input"]["credits"]["medical"]["general"] == 3_000_000


def test_optimize_validation() -> None:
    with _client() as c:
        res = c.post("/api/v1/couples/optimize", json={**BODY, "tax_year": 2026})
    assert res.status_code == 422
    assert res.json()["code"] == "validation_error"


def test_recommendations_require_key() -> None:
    with _client() as c:
        res = c.post("/api/v1/couples/recommendations", json=BODY)
    assert res.status_code == 503
    assert res.json()["code"] == "ai_unavailable"


class FakeClient:
    def generate(self, *, instructions: str, payload: str, output_type: type[Any]) -> Any:
        return LlmCoupleOutput(
            summary="부모님은 배우자가 공제받는 것이 유리합니다.",
            dependent_reasons=[LlmDependentReason(index=0, reason="의료비 문턱이 낮음")],
            tips=["신용카드는 총급여 25% 문턱을 넘는 쪽에 몰아주세요."],
        )


def test_recommendations_with_fake_client() -> None:
    client = _client("sk-test")
    client.app.dependency_overrides[get_recommendation_client] = FakeClient  # type: ignore[attr-defined]
    with client as c:
        res = c.post("/api/v1/couples/recommendations", json=BODY)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["dependent_reasons"][0]["recommended_to"] == "spouse"
    assert body["dependent_reasons"][0]["name"] == "부양가족 1"
    assert body["tips"]
