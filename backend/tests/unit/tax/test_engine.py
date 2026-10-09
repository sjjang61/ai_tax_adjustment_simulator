"""계산 파이프라인 통합 동작."""

from typing import Any

import pytest

from app.tax.engine import DISCLAIMER, RulesYearMismatchError, calculate
from app.tax.result import CreditMethod, TaxResult
from app.tax.rules import get_rules
from tests.factories import make_input


def _calc(**override: Any) -> TaxResult:
    inp = make_input(**override)
    return calculate(inp, get_rules(inp.tax_year))


def test_year_mismatch() -> None:
    with pytest.raises(RulesYearMismatchError):
        calculate(make_input(tax_year=2025), get_rules(2026))


def test_zero_income() -> None:
    r = _calc(income={"annual_earned_income": 0})
    assert r.tax_base == 0
    assert r.determined_tax == 0
    assert r.balance_due == 0
    assert r.applied_method is CreditMethod.ITEMIZED  # 동점이면 특별공제 방식


def test_determined_tax_never_negative_and_credits_capped() -> None:
    r = _calc(
        income={"annual_earned_income": 20_000_000},
        taxpayer={"is_homeless": True},
        credits={"monthly_rent": 10_000_000, "pension_savings": 6_000_000},
    )
    assert r.determined_tax == 0
    assert r.total_tax_credit == r.calculated_tax
    capped = [c for c in r.tax_credits if "산출세액 한도" in c.description]
    assert capped and all(c.limited for c in capped)


def test_standard_credit_chosen_when_better() -> None:
    r = _calc(income={"annual_earned_income": 30_000_000})
    assert r.applied_method is CreditMethod.STANDARD
    assert any(c.key == "standard_credit" and c.amount == 130_000 for c in r.tax_credits)
    assert "standard_credit_selected" in {w.code for w in r.warnings}
    itemized, standard = r.method_comparison
    assert standard.determined_tax < itemized.determined_tax


def test_itemized_chosen_and_standard_excludes_special_income_deduction() -> None:
    r = _calc(
        deductions={"health_insurance": 2_000_000, "employment_insurance": 400_000},
        credits={"insurance_general": 1_000_000},
    )
    assert r.applied_method is CreditMethod.ITEMIZED
    itemized, standard = r.method_comparison
    assert standard.tax_base - itemized.tax_base == 2_400_000
    assert itemized.determined_tax <= standard.determined_tax


def test_standard_method_marks_excluded_items() -> None:
    r = _calc(
        income={"annual_earned_income": 30_000_000},
        credits={"insurance_general": 100_000},
    )
    assert r.applied_method is CreditMethod.STANDARD
    special = next(c for c in r.tax_credits if c.key == "special_credit")
    assert special.amount == 0
    assert "표준세액공제" in special.description


def test_balance_due_and_local_tax() -> None:
    r = _calc(prepaid_tax={"withholding": 1_000_009, "previous_employer": 0})
    assert r.prepaid_tax == 1_000_009
    raw = r.determined_tax - r.prepaid_tax
    assert r.balance_due == (raw // 10 * 10 if raw >= 0 else -(-raw // 10 * 10))
    assert r.local_income_tax.determined_tax == r.determined_tax // 10
    assert r.total_balance_due == r.balance_due + r.local_income_tax.balance_due
    assert r.disclaimer == DISCLAIMER


def test_aggregate_limit_applied_in_pipeline() -> None:
    r = _calc(
        income={"annual_earned_income": 150_000_000},
        deductions={
            "long_term_mortgage_interest": 20_000_000,
            "mortgage_type": "fixed_and_non_deferred_15y",
            "card": {"credit": 100_000_000, "traditional_market": 10_000_000},
        },
    )
    aggregate = next(x for x in r.income_deductions if x.key == "aggregate_limit")
    # 장기주택저당 20,000,000 + 카드 4,500,000 = 24,500,000 → 한도 이내
    assert aggregate.amount == 0
    r2 = _calc(
        income={"annual_earned_income": 150_000_000},
        deductions={
            "long_term_mortgage_interest": 20_000_000,
            "mortgage_type": "fixed_and_non_deferred_15y",
            "card": {"credit": 100_000_000, "traditional_market": 10_000_000},
            "venture_fund": 10_000_000,
        },
    )
    aggregate2 = next(x for x in r2.income_deductions if x.key == "aggregate_limit")
    assert aggregate2.amount == -500_000


def test_result_is_immutable() -> None:
    r = _calc()
    with pytest.raises(Exception):  # noqa: B017 - pydantic ValidationError
        r.determined_tax = 0  # type: ignore[misc]


def test_tax_rate_label() -> None:
    assert _calc(income={"annual_earned_income": 50_000_000}).tax_rate == "15%"


def test_count_items_use_count_unit() -> None:
    r = _calc(
        taxpayer={"is_married": True},
        dependents=[{"relation": "lineal_descendant", "birth_year": 2012}],
    )
    personal = r.income_deductions[0]
    assert personal.key == "personal_deduction"
    assert personal.applied_unit == "count"
    assert personal.applied_amount == 2
    pension = r.income_deductions[1]
    assert pension.applied_unit == "won"
    child = next(c for c in r.tax_credits if c.key == "child_credit")
    assert child.applied_unit == "count"
