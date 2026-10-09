"""사업자(공동사업장) 소득 배분 — 손익분배비율대로 나눈다 (소득세법 제43조)."""

from typing import Any

import pytest
from pydantic import ValidationError

from app.tax.business import BusinessRecord, allocate
from app.tax.rules import get_rules

RULES = get_rules(2025)


def _record(**override: Any) -> BusinessRecord:
    data: dict[str, Any] = {
        "name": "공동 스튜디오",
        "tax_year": 2025,
        "revenue": 100_000_000,
        "expense_method": "book",
        "expenses": 40_000_000,
        "withholding_tax": 3_000_000,
        "partners": [{"name": "김대표", "share": 5}, {"name": "이대표", "share": 5}],
    }
    data.update(override)
    return BusinessRecord.model_validate(data)


def test_business_level_income_is_computed_first() -> None:
    a = allocate(_record(), RULES)
    assert (a.revenue, a.expenses, a.income_amount, a.withholding_tax) == (
        100_000_000,
        40_000_000,
        60_000_000,
        3_000_000,
    )


def test_five_to_five() -> None:
    a = allocate(_record(), RULES)
    assert [
        (p.ratio, p.revenue, p.expenses, p.income_amount, p.withholding_tax) for p in a.partners
    ] == [
        ("50%", 50_000_000, 20_000_000, 30_000_000, 1_500_000),
        ("50%", 50_000_000, 20_000_000, 30_000_000, 1_500_000),
    ]


def test_six_to_four() -> None:
    a = allocate(_record(partners=[{"name": "A", "share": 6}, {"name": "B", "share": 4}]), RULES)
    assert [p.income_amount for p in a.partners] == [36_000_000, 24_000_000]
    assert [p.ratio for p in a.partners] == ["60%", "40%"]


def test_remainder_goes_to_last_partner_and_sums_are_exact() -> None:
    a = allocate(
        _record(
            revenue=100_000_001,
            expenses=10,
            withholding_tax=1_000,
            partners=[{"name": n, "share": 1} for n in "ABC"],
        ),
        RULES,
    )
    assert sum(p.revenue for p in a.partners) == 100_000_001
    assert sum(p.expenses for p in a.partners) == 10
    assert sum(p.withholding_tax for p in a.partners) == 1_000
    assert [p.revenue for p in a.partners] == [33_333_333, 33_333_333, 33_333_335]
    assert [p.ratio for p in a.partners] == ["33.33%", "33.33%", "33.33%"]


def test_rate_method_and_estimated_withholding_at_business_level() -> None:
    a = allocate(
        _record(
            expense_method="rate",
            expense_rate="64.1",
            withholding_tax=None,
            partners=[{"name": "A", "share": 6}, {"name": "B", "share": 4}],
        ),
        RULES,
    )
    assert a.expenses == 64_100_000
    assert a.withholding_tax == 3_000_000  # 수입 × 3% 추정
    assert [p.withholding_tax for p in a.partners] == [1_800_000, 1_200_000]


def test_loss_is_shared() -> None:
    a = allocate(_record(revenue=10_000_000, expenses=30_000_000), RULES)
    assert [p.income_amount for p in a.partners] == [-10_000_000, -10_000_000]


def test_partner_business_income_input_reproduces_share() -> None:
    a = allocate(
        _record(
            partners=[{"name": "A", "share": 6, "simulation_id": 3}, {"name": "B", "share": 4}]
        ),
        RULES,
    )
    bi = a.partners[0].business_income
    assert bi.expense_method == "book"
    assert (bi.revenue, bi.expenses, bi.withholding_tax) == (60_000_000, 24_000_000, 1_800_000)
    assert bi.name == "공동 스튜디오 (지분 60%)"
    assert a.partners[0].simulation_id == 3
    assert a.partners[1].simulation_id is None


def test_single_owner() -> None:
    a = allocate(_record(partners=[{"name": "단독", "share": 1}]), RULES)
    assert a.partners[0].ratio == "100%"
    assert a.partners[0].income_amount == 60_000_000


def test_validation() -> None:
    with pytest.raises(ValidationError):
        _record(partners=[])
    with pytest.raises(ValidationError):
        _record(partners=[{"name": "A", "share": 0}])
    with pytest.raises(ValidationError):
        _record(partners=[{"name": f"P{i}", "share": 1} for i in range(11)])
    with pytest.raises(ValidationError):
        _record(expense_rate="101")
    with pytest.raises(ValidationError):  # 같은 연말정산 시뮬레이션을 두 대표에 연결할 수 없음
        _record(
            partners=[
                {"name": "A", "share": 1, "simulation_id": 1},
                {"name": "B", "share": 1, "simulation_id": 1},
            ]
        )
