"""맞벌이 부부 부양가족 배분 최적화."""

from itertools import product
from typing import Any

import pytest
from pydantic import ValidationError

from app.tax.couple import (
    MAX_SHARED_DEPENDENTS,
    CoupleInput,
    Spouse,
    build_individual,
    evaluate_assignment,
    medical_category,
    optimize,
)
from app.tax.rules import get_rules
from tests.factories import input_dict

RULES = get_rules(2025)
P, S = Spouse.PRIMARY, Spouse.SPOUSE


def _couple(
    shared: list[dict[str, Any]],
    primary_gross: int = 80_000_000,
    spouse_gross: int = 40_000_000,
    **extra: Any,
) -> CoupleInput:
    return CoupleInput.model_validate(
        {
            "tax_year": 2025,
            "primary": input_dict(
                income={"annual_earned_income": primary_gross},
                taxpayer={"birth_year": 1985, "is_married": True},
            ),
            "spouse": input_dict(
                income={"annual_earned_income": spouse_gross},
                taxpayer={"birth_year": 1987, "is_married": True, "is_female": True},
            ),
            "shared_dependents": shared,
            **extra,
        }
    )


def _dep(**kw: Any) -> dict[str, Any]:
    return {"relation": "lineal_descendant", "birth_year": 2015, **kw}


# ------------------------------------------------------------------ 의료비 분류
@pytest.mark.parametrize(
    ("dep", "expected"),
    [
        ({"relation": "lineal_ascendant", "birth_year": 1960}, "specific"),  # 65세
        ({"relation": "lineal_ascendant", "birth_year": 1961}, "general"),  # 64세
        ({"birth_year": 2019}, "specific"),  # 개시일 현재 5세
        ({"birth_year": 2018}, "specific"),  # 개시일 현재 6세
        ({"birth_year": 2017}, "general"),  # 개시일 현재 7세
        ({"birth_year": 2010, "disabled": True}, "specific"),
    ],
)
def test_medical_category(dep: dict[str, Any], expected: str) -> None:
    couple = _couple([_dep(**dep)])
    assert medical_category(couple.shared_dependents[0], 2025, RULES) == expected


# ------------------------------------------------------------------ 개인 입력 구성
def test_build_individual_appends_dependents_and_expenses() -> None:
    couple = _couple(
        [
            _dep(
                name="첫째",
                medical_expense=1_000_000,
                education_kind="school",
                education_amount=2_000_000,
            ),
            _dep(relation="lineal_ascendant", birth_year=1950, medical_expense=3_000_000),
        ],
    )
    built = build_individual(couple.primary, list(couple.shared_dependents), 2025, RULES)
    assert [d.name for d in built.dependents] == ["첫째", ""]
    assert built.credits.medical.general == 1_000_000
    assert built.credits.medical.specific == 3_000_000
    assert [(e.kind, e.amount, e.label) for e in built.credits.education] == [
        ("school", 2_000_000, "첫째")
    ]
    assert couple.primary.dependents == ()  # 원본 불변


def test_dependent_without_education_amount_adds_no_education() -> None:
    couple = _couple([_dep(education_kind="school", education_amount=0)])
    built = build_individual(couple.primary, list(couple.shared_dependents), 2025, RULES)
    assert built.credits.education == ()


# ------------------------------------------------------------------ 최적화
def test_medical_only_dependent_goes_to_lower_salary_spouse() -> None:
    # 59세 부모: 기본공제 나이 요건 미충족, 의료비만 있음 → 총급여 3% 문턱이 낮은 배우자가 유리
    couple = _couple(
        [
            {
                "relation": "lineal_ascendant",
                "birth_year": 1966,
                "medical_expense": 3_000_000,
                "assigned_to": "primary",
            }
        ]
    )
    result = optimize(couple, RULES)
    assert result.best.assignment == (S,)
    assert result.baseline.assignment == (P,)
    assert result.saving > 0
    assert result.saving == result.baseline.combined_total_balance_due - (
        result.best.combined_total_balance_due
    )


def test_tie_keeps_current_assignment() -> None:
    # 나이 요건 미충족·지출 없음 → 누구에게 가도 같음 → 현재 배분 유지
    couple = _couple(
        [{"relation": "lineal_ascendant", "birth_year": 1980, "assigned_to": "spouse"}]
    )
    result = optimize(couple, RULES)
    assert result.best.assignment == (S,)
    assert result.saving == 0


def test_best_is_minimum_over_all_assignments() -> None:
    couple = _couple(
        [
            _dep(
                name="첫째",
                birth_year=2012,
                medical_expense=2_000_000,
                education_kind="school",
                education_amount=3_000_000,
            ),
            _dep(name="둘째", birth_year=2020, medical_expense=500_000),
            {
                "name": "어머니",
                "relation": "lineal_ascendant",
                "birth_year": 1952,
                "medical_expense": 4_000_000,
                "assigned_to": "spouse",
            },
        ]
    )
    result = optimize(couple, RULES)
    assert result.evaluated_count == 8
    totals = [
        evaluate_assignment(couple, assignment, RULES).combined_total_balance_due
        for assignment in product((P, S), repeat=3)
    ]
    assert result.best.combined_total_balance_due == min(totals)
    assert result.best.combined_total_balance_due <= result.baseline.combined_total_balance_due
    assert len(result.alternatives) <= 3
    assert all(
        alt.combined_total_balance_due >= result.best.combined_total_balance_due
        for alt in result.alternatives
    )
    # 최적안의 개인별 입력·결과가 함께 반환된다
    names_primary = {d.name for d in result.best_primary_input.dependents}
    names_spouse = {d.name for d in result.best_spouse_input.dependents}
    assert names_primary | names_spouse == {"첫째", "둘째", "어머니"}
    assert not names_primary & names_spouse  # 한 명은 한 사람만 공제
    assert result.best_primary_result.determined_tax == result.best.primary_determined_tax


def test_no_shared_dependents() -> None:
    result = optimize(_couple([]), RULES)
    assert result.evaluated_count == 1
    assert result.best.assignment == ()
    assert result.saving == 0


def test_plan_totals_are_sum_of_individuals() -> None:
    couple = _couple([_dep()])
    plan = evaluate_assignment(couple, (P,), RULES)
    assert plan.combined_total_balance_due == (
        plan.primary_total_balance_due + plan.spouse_total_balance_due
    )
    assert plan.combined_determined_tax == plan.primary_determined_tax + plan.spouse_determined_tax


# ------------------------------------------------------------------ 입력 검증
def test_validation() -> None:
    with pytest.raises(ValidationError):  # 귀속연도 불일치
        CoupleInput.model_validate(
            {"tax_year": 2025, "primary": input_dict(), "spouse": input_dict(tax_year=2026)}
        )
    with pytest.raises(ValidationError):  # 배우자는 공유 부양가족이 될 수 없음
        _couple([{"relation": "spouse", "birth_year": 1990}])
    with pytest.raises(ValidationError):  # 본인 교육비는 각자 입력
        _couple([_dep(education_kind="self", education_amount=1)])
    with pytest.raises(ValidationError):
        _couple([_dep() for _ in range(MAX_SHARED_DEPENDENTS + 1)])
    with pytest.raises(ValidationError):  # 알 수 없는 필드 거부
        _couple([_dep(unknown=1)])
