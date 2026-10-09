from decimal import Decimal
from typing import Any

import pytest

from app.services.carry_over import CarryOverError, FieldMapping, carry_over
from app.services.schema_migration import SchemaVersionError, migrate_input
from tests.factories import input_dict, make_input


def _codes(result: Any) -> set[str]:
    return {w.code for w in result.warnings}


def test_does_not_mutate_source() -> None:
    src = make_input(taxpayer={"marriage_registered_this_year": True})
    result = carry_over(src, 2026)
    assert src.tax_year == 2025
    assert src.taxpayer.marriage_registered_this_year is True
    assert result.input.tax_year == 2026
    assert result.input.taxpayer.marriage_registered_this_year is False


def test_target_year_must_be_later() -> None:
    with pytest.raises(CarryOverError):
        carry_over(make_input(), 2025)


def test_age_requirement_changes() -> None:
    src = make_input(
        taxpayer={"is_married": True},
        dependents=[
            {"relation": "lineal_descendant", "birth_year": 2005},  # 20 → 21: 기본공제 제외
            {"relation": "lineal_ascendant", "birth_year": 1966},  # 59 → 60: 기본공제 대상
            {"relation": "lineal_ascendant", "birth_year": 1956},  # 69 → 70: 경로우대
            {"relation": "lineal_descendant", "birth_year": 2018},  # 7 → 8: 자녀세액공제
        ],
    )
    codes = _codes(carry_over(src, 2026))
    assert {
        "carry_over_lost_basic",
        "carry_over_gained_basic",
        "carry_over_elderly",
        "carry_over_child_credit",
    } <= codes


def test_child_credit_lost_for_disabled_adult_child_is_not_reported() -> None:
    # 장애인 자녀는 나이와 무관하게 기본공제 대상, 자녀세액공제도 유지
    src = make_input(
        taxpayer={"is_married": True},
        dependents=[{"relation": "lineal_descendant", "birth_year": 2005, "disabled": True}],
    )
    assert "carry_over_lost_child_credit" not in _codes(carry_over(src, 2026))


def test_lost_child_credit_when_rule_age_changes() -> None:
    src = make_input(
        taxpayer={"is_married": True},
        dependents=[{"relation": "lineal_descendant", "birth_year": 2015}],
    )
    from app.tax import rules as rules_module

    original = rules_module._REGISTRY[2026]
    patched = original.model_copy(
        update={"child_credit": original.child_credit.model_copy(update={"min_age": 12})}
    )
    rules_module._REGISTRY[2026] = patched
    try:
        assert "carry_over_lost_child_credit" in _codes(carry_over(src, 2026))
    finally:
        rules_module._REGISTRY[2026] = original


@pytest.mark.parametrize(
    ("rate", "expected"),
    [(Decimal("3.5"), 51_750_000), (Decimal("-10"), 45_000_000), (Decimal("0.0001"), 50_000_050)],
)
def test_salary_increase(rate: Decimal, expected: int) -> None:
    result = carry_over(make_input(), 2026, salary_increase_rate=rate)
    assert result.input.income.annual_earned_income == expected
    assert "carry_over_salary_adjusted" in _codes(result)


def test_salary_decrease_never_below_non_taxable() -> None:
    src = make_input(income={"annual_earned_income": 10_000_000, "non_taxable_income": 9_000_000})
    result = carry_over(src, 2026, salary_increase_rate=Decimal("-50"))
    assert result.input.income.annual_earned_income == 9_000_000


def test_mapping_table_rename_remove_add() -> None:
    mappings = {
        (2025, 2026): (
            FieldMapping(source="credits.irp", target="credits.pension_savings", note="이름 변경"),
            FieldMapping(source="credits.monthly_rent", target=None, note="월세 폐지"),
            FieldMapping(source="credits.insurance_disabled", target=None, note="빈 값"),
            FieldMapping(source="credits.not_there", target="credits.x", note="없는 항목"),
            FieldMapping(source=None, target="deductions.venture_fund", note="신설", default=7),
        )
    }
    src = make_input(credits={"irp": 1_000, "monthly_rent": 500}, deductions={"venture_fund": 3})
    result = carry_over(src, 2026, mappings=mappings)
    assert result.input.credits.pension_savings == 1_000
    assert result.input.credits.irp == 0
    assert result.input.credits.monthly_rent == 0
    assert result.input.deductions.venture_fund == 3  # 신설 항목 기본값은 기존 값을 덮어쓰지 않음
    unmapped = [w for w in result.warnings if w.code == "carry_over_unmapped"]
    assert len(unmapped) == 1 and "월세 폐지" in unmapped[0].message
    assert {"carry_over_mapped", "carry_over_new_item"} <= _codes(result)


def test_migration_chain() -> None:
    data = input_dict()
    assert migrate_input(data, 1) == data

    def v1_to_v2(d: dict[str, Any]) -> dict[str, Any]:
        return {**d, "v2": True}

    def v2_to_v3(d: dict[str, Any]) -> dict[str, Any]:
        return {**d, "v3": True}

    out = migrate_input(data, 1, target_version=3, migrations={1: v1_to_v2, 2: v2_to_v3})
    assert out["v2"] and out["v3"]
    assert "v2" not in data  # 원본 불변

    with pytest.raises(SchemaVersionError):
        migrate_input(data, 1, target_version=3, migrations={1: v1_to_v2})
    with pytest.raises(SchemaVersionError):
        migrate_input(data, 5)
