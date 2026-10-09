import json
from typing import Any, get_args
from unittest.mock import MagicMock

import pytest
from openai import APITimeoutError

from app.core.errors import AppError
from app.schemas.recommendation import (
    ADJUSTABLE_FIELDS,
    AdjustableField,
    LlmAdjustment,
    LlmOutput,
    LlmRecommendation,
    RecommendationCategory,
)
from app.services.ai_recommendation import (
    INSTRUCTIONS,
    OpenAIRecommendationClient,
    apply_adjustment,
    build_payload,
    recommend,
)
from app.tax.engine import calculate
from app.tax.inputs import SimulationInput
from app.tax.rules import get_rules
from tests.factories import make_input

# 골든 사례(총급여 5,760만원, 연금저축 600만원 납입, IRP 0원)
BASE = make_input(
    income={"annual_earned_income": 60_000_000, "non_taxable_income": 2_400_000},
    prepaid_tax={"withholding": 3_000_000},
    taxpayer={"birth_year": 1988},
    deductions={
        "national_pension": 2_592_000,
        "health_insurance": 2_270_000,
        "employment_insurance": 518_000,
        "card": {"credit": 20_000_000, "debit_cash": 5_000_000, "public_transport": 800_000},
    },
    credits={
        "pension_savings": 6_000_000,
        "insurance_general": 1_000_000,
        "medical": {"specific": 3_000_000},
    },
)


def _rec(
    title: str,
    field: str | None = None,
    amount: int = 0,
    category: RecommendationCategory = RecommendationCategory.TAX_CREDIT,
) -> LlmRecommendation:
    return LlmRecommendation(
        title=title,
        category=category,
        reason="이유",
        action="할 일",
        adjustment=None if field is None else LlmAdjustment(field=field, additional_amount=amount),  # type: ignore[arg-type]
    )


class FakeClient:
    def __init__(self, output: LlmOutput | Exception) -> None:
        self.output = output
        self.calls: list[dict[str, str]] = []

    def generate(self, *, instructions: str, payload: str, output_type: type[Any]) -> Any:
        self.calls.append({"instructions": instructions, "payload": payload})
        if isinstance(self.output, Exception):
            raise self.output
        return self.output


def test_saving_is_computed_by_engine() -> None:
    client = FakeClient(
        LlmOutput(summary="요약", recommendations=[_rec("IRP 추가 납입", "credits.irp", 3_000_000)])
    )
    res = recommend(BASE, client, "gpt-5.6-luna")
    rec = res.recommendations[0]
    # IRP 300만원 × 12%(총급여 5,500만원 초과) = 360,000원 + 지방소득세 36,000원
    assert rec.estimated_saving == 396_000
    assert rec.adjustment_label == "퇴직연금(IRP) 납입액"
    assert rec.adjusted_input is not None
    assert rec.adjusted_input.credits.irp == 3_000_000
    assert res.base_total_balance_due == -699_930
    assert res.model == "gpt-5.6-luna"
    assert res.discarded_count == 0


def test_ineffective_and_invalid_suggestions_are_discarded() -> None:
    client = FakeClient(
        LlmOutput(
            summary="요약",
            recommendations=[
                _rec("연금저축 한도 초과", "credits.pension_savings", 1_000_000),  # 이미 600만원
                _rec("음수 금액", "credits.irp", -100),
                _rec("0원", "credits.irp", 0),
                _rec(
                    "부양가족 확인", category=RecommendationCategory.ELIGIBILITY_CHECK
                ),  # 조정 없음 → 유지
                _rec("IRP", "credits.irp", 1_000_000),
            ],
        )
    )
    res = recommend(BASE, client, "m")
    assert [r.title for r in res.recommendations] == ["IRP", "부양가족 확인"]
    assert res.discarded_count == 3
    check = res.recommendations[1]
    assert check.estimated_saving is None and check.adjusted_input is None


def test_sorted_by_saving_and_capped_at_five() -> None:
    recs = [_rec(f"IRP {i}", "credits.irp", i * 500_000) for i in range(1, 8)]
    res = recommend(BASE, FakeClient(LlmOutput(summary="s", recommendations=recs)), "m")
    savings = [r.estimated_saving or 0 for r in res.recommendations]
    assert len(savings) == 5
    assert savings == sorted(savings, reverse=True)


def test_card_shift_moves_from_credit_card() -> None:
    adjusted = apply_adjustment(BASE, "deductions.card.debit_cash", 5_000_000)
    assert adjusted.deductions.card.debit_cash == 10_000_000
    assert adjusted.deductions.card.credit == 15_000_000
    assert adjusted.deductions.card.total == BASE.deductions.card.total  # 총 사용액 불변
    assert BASE.deductions.card.debit_cash == 5_000_000  # 원본 불변

    over = apply_adjustment(BASE, "deductions.card.traditional_market", 30_000_000)
    assert over.deductions.card.credit == 0
    assert over.deductions.card.traditional_market == 30_000_000


def test_apply_adjustment_rejects_unknown_field() -> None:
    with pytest.raises(ValueError):
        apply_adjustment(BASE, "income.annual_earned_income", 1)


def test_payload_excludes_personal_names() -> None:
    inp = make_input(
        taxpayer={"is_married": True},
        dependents=[{"name": "홍길동", "relation": "lineal_descendant", "birth_year": 2015}],
        credits={"education": [{"kind": "school", "amount": 1_000_000, "label": "김철수"}]},
    )
    payload = build_payload(inp)
    assert "홍길동" not in payload and "김철수" not in payload
    data = json.loads(payload)
    assert data["input"]["dependents"] == [
        {
            "relation": "lineal_descendant",
            "age": 10,
            "disabled": False,
            "income_amount": 0,
            "income_is_salary_only": False,
        }
    ]
    assert "birth_year" not in data["input"]["taxpayer"]
    assert data["input"]["taxpayer"]["age"] == 35
    assert data["adjustable_fields"] == ADJUSTABLE_FIELDS
    assert data["rules"]["tax_year"] == 2025
    # 익명화해도 계산 결과 숫자는 원본과 같다
    assert data["result"]["determined_tax"] == calculate(inp, get_rules(2025)).determined_tax


def test_instructions_forbid_llm_tax_calculation() -> None:
    assert "직접 계산" in INSTRUCTIONS
    assert "adjustable_fields" in INSTRUCTIONS


def test_client_error_becomes_502() -> None:
    client = FakeClient(APITimeoutError(request=MagicMock()))
    with pytest.raises(AppError) as exc:
        recommend(BASE, client, "m")
    assert exc.value.status_code == 502
    assert exc.value.code == "ai_failed"


def test_adjustable_fields_match_literal() -> None:
    assert set(get_args(AdjustableField)) == set(ADJUSTABLE_FIELDS)


def test_llm_output_schema_is_valid_for_openai_strict_mode() -> None:
    from openai.lib._pydantic import to_strict_json_schema

    schema: dict[str, Any] = to_strict_json_schema(LlmOutput)
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {"summary", "recommendations"}


def test_openai_client_uses_structured_output(monkeypatch: pytest.MonkeyPatch) -> None:
    client = OpenAIRecommendationClient(api_key="sk-test", model="gpt-5.6-luna", timeout=10)
    expected = LlmOutput(summary="s", recommendations=[])
    parse = MagicMock(return_value=MagicMock(output_parsed=expected))
    monkeypatch.setattr(client._client.responses, "parse", parse)
    assert client.generate(instructions="i", payload="p", output_type=LlmOutput) == expected
    kwargs = parse.call_args.kwargs
    assert kwargs["model"] == "gpt-5.6-luna"
    assert kwargs["text_format"] is LlmOutput
    assert kwargs["store"] is False

    parse.return_value = MagicMock(output_parsed=None)
    with pytest.raises(ValueError):
        client.generate(instructions="i", payload="p", output_type=LlmOutput)


def test_input_type_is_reused() -> None:
    assert isinstance(BASE, SimulationInput)
