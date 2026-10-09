"""인적공제와 공제 요건 판정."""

from typing import Any

import pytest

from app.tax.deductions.personal import personal_deduction
from app.tax.eligibility import evaluate
from app.tax.rules import get_rules
from tests.factories import make_input

RULES = get_rules(2025)


def _codes(inp: Any) -> set[str]:
    return {w.code for w in evaluate(inp, RULES).warnings}


def test_self_only() -> None:
    e = evaluate(make_input(), RULES)
    item = personal_deduction(e, RULES)
    assert item.amount == 1_500_000
    assert e.warnings == ()


@pytest.mark.parametrize(
    ("birth_year", "eligible"),
    [(1966, False), (1965, True), (1964, True)],  # 2025년 기준 60세 = 1965년생
)
def test_ascendant_age_boundary(birth_year: int, eligible: bool) -> None:
    inp = make_input(dependents=[{"relation": "lineal_ascendant", "birth_year": birth_year}])
    assert evaluate(inp, RULES).persons[1].basic_eligible is eligible
    assert ("dependent_age_requirement" in _codes(inp)) is (not eligible)


@pytest.mark.parametrize(
    ("birth_year", "eligible"), [(2005, True), (2004, False), (2025, True)]
)  # 20세 이하
def test_descendant_age_boundary(birth_year: int, eligible: bool) -> None:
    inp = make_input(dependents=[{"relation": "lineal_descendant", "birth_year": birth_year}])
    assert evaluate(inp, RULES).persons[1].basic_eligible is eligible


@pytest.mark.parametrize(
    ("birth_year", "eligible"), [(2005, True), (2000, False), (1965, True), (1966, False)]
)
def test_sibling_age(birth_year: int, eligible: bool) -> None:
    inp = make_input(dependents=[{"relation": "sibling", "birth_year": birth_year}])
    assert evaluate(inp, RULES).persons[1].basic_eligible is eligible


def test_disabled_dependent_ignores_age() -> None:
    inp = make_input(
        taxpayer={"is_married": True},
        dependents=[{"relation": "lineal_descendant", "birth_year": 1990, "disabled": True}],
    )
    e = evaluate(inp, RULES)
    assert e.persons[1].basic_eligible
    item = personal_deduction(e, RULES)
    assert item.amount == 1_500_000 * 2 + 2_000_000


@pytest.mark.parametrize(
    ("amount", "salary_only", "eligible"),
    [
        (1_000_000, False, True),
        (1_000_001, False, False),
        (5_000_000, True, True),
        (5_000_001, True, False),
    ],
)
def test_dependent_income_requirement(amount: int, salary_only: bool, eligible: bool) -> None:
    inp = make_input(
        dependents=[
            {
                "relation": "spouse",
                "birth_year": 1990,
                "income_amount": amount,
                "income_is_salary_only": salary_only,
            }
        ]
    )
    assert evaluate(inp, RULES).persons[1].basic_eligible is eligible
    assert ("dependent_income_requirement" in _codes(inp)) is (not eligible)


def test_elderly_boundary_70() -> None:
    inp = make_input(
        dependents=[
            {"relation": "lineal_ascendant", "birth_year": 1955},  # 70세
            {"relation": "lineal_ascendant", "birth_year": 1956},  # 69세
        ]
    )
    e = evaluate(inp, RULES)
    assert [p.elderly for p in e.persons[1:]] == [True, False]
    assert personal_deduction(e, RULES).amount == 1_500_000 * 3 + 1_000_000


def test_duplicate_spouse_and_unborn() -> None:
    inp = make_input(
        dependents=[
            {"relation": "spouse", "birth_year": 1990},
            {"relation": "spouse", "birth_year": 1991},
            {"relation": "lineal_descendant", "birth_year": 2026},
        ]
    )
    codes = _codes(inp)
    assert {"duplicate_spouse", "dependent_not_born"} <= codes
    assert len(evaluate(inp, RULES).basic_persons) == 2


def test_female_deduction() -> None:
    inp = make_input(
        income={"annual_earned_income": 30_000_000},
        taxpayer={"is_female": True, "is_married": True},
    )
    e = evaluate(inp, RULES)
    assert e.female_deduction
    assert personal_deduction(e, RULES).amount == 2_000_000


@pytest.mark.parametrize(
    ("gross", "eligible"),
    [
        (41_470_588, True),  # 근로소득금액 30,000,000원 (정확히 한도)
        (41_470_589, False),  # 근로소득금액 30,000,001원
    ],
)
def test_female_deduction_income_limit(gross: int, eligible: bool) -> None:
    inp = make_input(
        income={"annual_earned_income": gross},
        taxpayer={"is_female": True, "is_married": True},
    )
    assert evaluate(inp, RULES).female_deduction is eligible


def test_female_household_head_needs_dependent() -> None:
    inp = make_input(
        income={"annual_earned_income": 30_000_000},
        taxpayer={"is_female": True, "is_household_head": True},
    )
    assert not evaluate(inp, RULES).female_deduction


def test_single_parent_overrides_female() -> None:
    inp = make_input(
        income={"annual_earned_income": 30_000_000},
        taxpayer={"is_female": True, "is_household_head": True},
        dependents=[{"relation": "lineal_descendant", "birth_year": 2015}],
    )
    e = evaluate(inp, RULES)
    assert e.single_parent_deduction and not e.female_deduction
    assert "female_and_single_parent" in _codes(inp)
    assert personal_deduction(e, RULES).amount == 3_000_000 + 1_000_000


def test_child_credit_eligibility_age_8() -> None:
    inp = make_input(
        dependents=[
            {"relation": "lineal_descendant", "birth_year": 2017},  # 8세
            {"relation": "lineal_descendant", "birth_year": 2018},  # 7세
        ]
    )
    e = evaluate(inp, RULES)
    assert e.child_credit_count == 1
    assert e.eligible_child_count == 2


def test_birth_warnings() -> None:
    inp = make_input(
        dependents=[
            {
                "relation": "lineal_descendant",
                "birth_year": 2025,
                "born_or_adopted_this_year": True,
            },
            {"relation": "sibling", "birth_year": 2025, "born_or_adopted_this_year": True},
        ]
    )
    codes = _codes(inp)
    assert {"birth_order_missing", "birth_relation_mismatch"} <= codes
    e = evaluate(inp, RULES)
    assert [p.birth_order for p in e.persons[1:]] == [1, None]


def test_housing_and_rent_requirements() -> None:
    inp = make_input(
        deductions={
            "housing_subscription": 1_000_000,
            "housing_rent_loan_repayment": 1_000_000,
            "long_term_mortgage_interest": 1_000_000,
        },
        credits={"monthly_rent": 1_000_000},
    )
    assert {
        "housing_subscription_not_homeless",
        "rent_loan_not_homeless",
        "mortgage_type_missing",
        "monthly_rent_not_homeless",
    } <= _codes(inp)


def test_salary_limits_for_subscription_and_rent() -> None:
    inp = make_input(
        income={"annual_earned_income": 90_000_000},
        taxpayer={"is_homeless": True},
        deductions={"housing_subscription": 1_000_000, "card": {"culture": 100}},
        credits={"monthly_rent": 1_000_000},
    )
    assert {
        "housing_subscription_salary_limit",
        "monthly_rent_salary_limit",
        "card_culture_salary_limit",
    } <= _codes(inp)


def test_marriage_and_unverified_rules_warnings() -> None:
    inp = make_input(tax_year=2026, taxpayer={"marriage_registered_this_year": True})
    codes = {w.code for w in evaluate(inp, get_rules(2026)).warnings}
    assert {"rules_unverified", "marriage_credit_once"} <= codes


def test_marriage_credit_unavailable_when_rule_missing() -> None:
    rules = RULES.model_copy(update={"marriage_credit": None})
    inp = make_input(taxpayer={"marriage_registered_this_year": True})
    assert "marriage_credit_unavailable" in {w.code for w in evaluate(inp, rules).warnings}


def test_spouse_dependent_implies_married() -> None:
    inp = make_input(
        dependents=[
            {"relation": "spouse", "birth_year": 1990},
            {"relation": "lineal_descendant", "birth_year": 2015},
        ]
    )
    assert not evaluate(inp, RULES).single_parent_deduction
