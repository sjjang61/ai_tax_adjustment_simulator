import json
from typing import Any
from unittest.mock import MagicMock

import pytest
from openai import APIConnectionError

from app.core.errors import AppError
from app.services.ai_couple import (
    COUPLE_INSTRUCTIONS,
    LlmCoupleOutput,
    LlmDependentReason,
    anonymize_couple,
    build_couple_payload,
    recommend_couple,
)
from app.tax.couple import CoupleInput, Spouse, optimize
from app.tax.rules import get_rules
from tests.factories import input_dict

COUPLE = CoupleInput.model_validate(
    {
        "tax_year": 2025,
        "primary": input_dict(
            income={"annual_earned_income": 80_000_000}, taxpayer={"is_married": True}
        ),
        "spouse": input_dict(
            income={"annual_earned_income": 40_000_000}, taxpayer={"is_married": True}
        ),
        "shared_dependents": [
            {
                "name": "홍길동",
                "relation": "lineal_ascendant",
                "birth_year": 1966,
                "medical_expense": 3_000_000,
            },
            {
                "name": "김철수",
                "relation": "lineal_descendant",
                "birth_year": 2012,
                "education_kind": "school",
                "education_amount": 2_000_000,
            },
        ],
    }
)


class FakeClient:
    def __init__(self, output: Any) -> None:
        self.output = output
        self.payloads: list[str] = []

    def generate(self, *, instructions: str, payload: str, output_type: type[Any]) -> Any:
        assert output_type is LlmCoupleOutput
        self.payloads.append(payload)
        if isinstance(self.output, Exception):
            raise self.output
        return self.output


def test_payload_is_anonymous_and_contains_engine_results() -> None:
    anonymous = anonymize_couple(COUPLE)
    result = optimize(anonymous, get_rules(2025))
    payload = build_couple_payload(anonymous, result)
    # 익명화해도 배분 결과는 원본과 같다
    assert result.best.assignment == optimize(COUPLE, get_rules(2025)).best.assignment
    assert "홍길동" not in payload and "김철수" not in payload
    data = json.loads(payload)
    assert data["primary"]["medical_threshold"] == 2_400_000
    assert data["spouse"]["medical_threshold"] == 1_200_000
    assert data["shared_dependents"][0]["recommended"] == "spouse"
    assert data["shared_dependents"][0]["medical_category"] == "general"
    assert data["saving"] == result.saving
    assert data["best"]["assignment"] == [a.value for a in result.best.assignment]


def test_reasons_mapped_to_names_and_engine_assignment() -> None:
    client = FakeClient(
        LlmCoupleOutput(
            summary="요약",
            dependent_reasons=[
                LlmDependentReason(index=0, reason="의료비 문턱이 낮은 배우자"),
                LlmDependentReason(index=9, reason="존재하지 않는 가족"),
            ],
            tips=["팁1", "팁2", "팁3", "팁4"],
        )
    )
    res = recommend_couple(COUPLE, client, "gpt-5.6-luna")
    assert [(r.name, r.recommended_to) for r in res.dependent_reasons] == [
        ("홍길동", Spouse.SPOUSE)
    ]
    assert res.tips == ["팁1", "팁2", "팁3"]
    assert res.model == "gpt-5.6-luna"
    assert "홍길동" not in client.payloads[0]


def test_ai_failure_becomes_502() -> None:
    with pytest.raises(AppError) as exc:
        recommend_couple(COUPLE, FakeClient(APIConnectionError(request=MagicMock())), "m")
    assert exc.value.status_code == 502


def test_instructions_keep_engine_as_source_of_truth() -> None:
    assert "배분을 바꾸거나" in COUPLE_INSTRUCTIONS
    assert "직접 계산하지" in COUPLE_INSTRUCTIONS
