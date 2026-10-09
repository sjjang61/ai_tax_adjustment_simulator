"""종합소득세: 근로 + 사업 + 기타소득."""

from typing import Any

import pytest
from pydantic import ValidationError

from app.tax.engine import calculate
from app.tax.global_income import (
    GlobalIncomeInput,
    business_line,
    calculate_global,
    other_line,
)
from app.tax.rules import get_rules
from tests.factories import input_dict, make_input

RULES = get_rules(2025)


def _inp(**override: Any) -> GlobalIncomeInput:
    data: dict[str, Any] = {
        "tax_year": 2025,
        "base": input_dict(income={"annual_earned_income": 50_000_000}),
        "business_incomes": [],
        "other_incomes": [],
    }
    data.update(override)
    return GlobalIncomeInput.model_validate(data)


# ------------------------------------------------------------------ 소득별 계산
def test_business_book_method_and_estimated_withholding() -> None:
    b = _inp(
        business_incomes=[
            {
                "name": "프리랜서",
                "revenue": 50_000_000,
                "expense_method": "book",
                "expenses": 20_000_000,
            }
        ]
    )
    line = business_line(b.business_incomes[0], RULES)
    assert (line.expenses, line.income_amount, line.withholding_tax) == (
        20_000_000,
        30_000_000,
        1_500_000,
    )
    assert "추정" in line.note


def test_business_rate_method_and_explicit_withholding() -> None:
    b = _inp(
        business_incomes=[
            {
                "name": "강의",
                "revenue": 30_000_000,
                "expense_method": "rate",
                "expense_rate": "64.1",
                "withholding_tax": 800_000,
            }
        ]
    )
    line = business_line(b.business_incomes[0], RULES)
    assert line.expenses == 19_230_000  # 30,000,000 × 64.1%
    assert line.income_amount == 10_770_000
    assert line.withholding_tax == 800_000


@pytest.mark.parametrize(
    ("kind", "revenue", "expenses", "expected_expenses", "expected_amount"),
    [
        ("deemed_expense", 5_000_000, 0, 3_000_000, 2_000_000),  # 60% 의제
        ("deemed_expense", 5_000_000, 4_000_000, 4_000_000, 1_000_000),  # 실제 경비가 더 크면 실제
        ("actual", 2_000_000, 500_000, 500_000, 1_500_000),
        ("actual", 1_000_000, 2_000_000, 2_000_000, 0),  # 기타소득금액은 0원 하한
    ],
)
def test_other_income_amount(
    kind: str, revenue: int, expenses: int, expected_expenses: int, expected_amount: int
) -> None:
    o = _inp(
        other_incomes=[{"name": "원고료", "kind": kind, "revenue": revenue, "expenses": expenses}]
    ).other_incomes[0]
    line = other_line(o, RULES)
    assert (line.expenses, line.income_amount) == (expected_expenses, expected_amount)
    assert line.withholding_tax == expected_amount * 20 // 100  # 기타소득금액의 20%


# ------------------------------------------------------------------ 분리과세 vs 종합과세
def _other(amount_after_60: int) -> dict[str, Any]:
    # 필요경비 60% 의제 → 기타소득금액 = 수입 × 40%
    return {"name": "강연료", "kind": "deemed_expense", "revenue": amount_after_60 * 10 // 4}


def test_separate_taxation_available_up_to_threshold_and_auto_picks_lower() -> None:
    r = calculate_global(_inp(other_incomes=[_other(3_000_000)]), RULES)
    assert len(r.options) == 2
    best = min(r.options, key=lambda o: o.total_burden)
    assert r.other_income_taxation == best.taxation
    # 총급여 5천만원(15% 구간)에서는 20% 분리과세보다 종합과세가 유리
    assert r.other_income_taxation == "comprehensive"


def test_separate_preferred_for_high_bracket() -> None:
    high = _inp(
        base=input_dict(income={"annual_earned_income": 150_000_000}),
        other_incomes=[_other(2_000_000)],
    )
    r = calculate_global(high, RULES)
    assert r.other_income_taxation == "separate"
    assert r.separate_tax == 400_000
    assert r.other_income_amount == 0  # 종합소득에 합산하지 않음
    assert r.prepaid.other_withholding == 0  # 분리과세 원천징수는 기납부세액에서 제외(과세 종결)


def test_over_threshold_must_be_comprehensive() -> None:
    r = calculate_global(_inp(other_incomes=[_other(3_000_001)]), RULES)
    assert len(r.options) == 1
    assert r.other_income_taxation == "comprehensive"


def test_forced_options() -> None:
    forced = calculate_global(
        _inp(other_incomes=[_other(1_000_000)], other_income_taxation="separate"), RULES
    )
    assert forced.other_income_taxation == "separate"
    not_allowed = calculate_global(
        _inp(other_incomes=[_other(5_000_000)], other_income_taxation="separate"), RULES
    )
    assert not_allowed.other_income_taxation == "comprehensive"
    assert any(w.code == "separate_taxation_not_allowed" for w in not_allowed.warnings)
    comp = calculate_global(
        _inp(
            base=input_dict(income={"annual_earned_income": 150_000_000}),
            other_incomes=[_other(1_000_000)],
            other_income_taxation="comprehensive",
        ),
        RULES,
    )
    assert comp.other_income_taxation == "comprehensive"


def test_no_other_income() -> None:
    r = calculate_global(_inp(), RULES)
    assert r.other_income_taxation == "none"
    assert len(r.options) == 1


# ------------------------------------------------------------------ 기납부세액·결과
def test_prepaid_uses_year_end_settlement_determined_tax_by_default() -> None:
    inp = _inp(
        business_incomes=[
            {"name": "부업", "revenue": 10_000_000, "expense_method": "book", "expenses": 2_000_000}
        ],
        interim_prepayment=100_000,
    )
    r = calculate_global(inp, RULES)
    settled = calculate(make_input(income={"annual_earned_income": 50_000_000}), RULES)
    assert r.prepaid.earned_settled == settled.determined_tax
    assert r.prepaid.business_withholding == 300_000
    assert r.prepaid.interim_prepayment == 100_000
    assert r.prepaid.total == settled.determined_tax + 300_000 + 100_000
    assert r.tax_result.prepaid_tax == r.prepaid.total
    assert r.total_balance_due == r.tax_result.total_balance_due
    assert r.comprehensive_income_amount == r.earned_income_amount + 8_000_000
    # 근로소득만 있을 때보다 결정세액이 늘어난다
    assert r.tax_result.determined_tax > settled.determined_tax


def test_prepaid_override() -> None:
    r = calculate_global(_inp(earned_prepaid_tax=1_234_000), RULES)
    assert r.prepaid.earned_settled == 1_234_000


def test_only_business_income() -> None:
    inp = _inp(
        base=input_dict(income={"annual_earned_income": 0}),
        business_incomes=[
            {"name": "사업", "revenue": 40_000_000, "expense_method": "rate", "expense_rate": "30"}
        ],
    )
    r = calculate_global(inp, RULES)
    assert r.earned_income_amount == 0
    assert r.business_income_amount == 28_000_000
    assert r.prepaid.earned_settled == 0
    std = next(c for c in r.tax_result.tax_credits if c.key == "standard_credit")
    assert std.amount == 70_000
    assert [line.kind for line in r.income_lines] == ["business"]


def test_business_loss_warning() -> None:
    r = calculate_global(
        _inp(
            business_incomes=[
                {
                    "name": "적자 사업",
                    "revenue": 10_000_000,
                    "expense_method": "book",
                    "expenses": 80_000_000,
                }
            ]
        ),
        RULES,
    )
    assert r.business_income_amount == -70_000_000
    assert r.comprehensive_income_amount == 0
    assert any(w.code == "business_loss" for w in r.warnings)


def test_disclaimer_mentions_global_income_filing() -> None:
    r = calculate_global(_inp(), RULES)
    assert "종합소득세" in r.disclaimer


def test_validation() -> None:
    with pytest.raises(ValidationError):
        _inp(base=input_dict(tax_year=2026))
    with pytest.raises(ValidationError):
        _inp(
            business_incomes=[
                {"name": "x", "revenue": 1, "expense_method": "rate", "expense_rate": "100.1"}
            ]
        )
    with pytest.raises(ValidationError):
        _inp(other_incomes=[{"name": "x", "kind": "deemed_expense", "revenue": 1, "x": 1}])
