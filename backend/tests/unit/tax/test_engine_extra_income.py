"""근로소득 외 종합소득(사업·기타소득금액)이 있을 때의 엔진 동작."""

from decimal import Decimal
from typing import Any

from app.tax.engine import calculate
from app.tax.money import truncate_won
from app.tax.result import TaxResult
from app.tax.rules import get_rules
from tests.factories import make_input

RULES = get_rules(2025)


def _calc(extra: int = 0, **override: Any) -> TaxResult:
    return calculate(make_input(**override), RULES, extra_income=extra)


def _credit(r: TaxResult, key: str) -> int:
    return next(c.amount for c in r.tax_credits if c.key == key)


def test_zero_extra_income_is_identical_to_year_end_settlement() -> None:
    inp = make_input(
        income={"annual_earned_income": 60_000_000},
        deductions={"health_insurance": 2_000_000, "card": {"credit": 30_000_000}},
        credits={"pension_savings": 6_000_000, "medical": {"specific": 3_000_000}},
    )
    assert calculate(inp, RULES, extra_income=0) == calculate(inp, RULES)


def test_extra_income_raises_tax_base() -> None:
    base = _calc(income={"annual_earned_income": 50_000_000})
    mixed = _calc(20_000_000, income={"annual_earned_income": 50_000_000})
    assert mixed.tax_base - base.tax_base == 20_000_000
    assert mixed.earned_income_amount == base.earned_income_amount  # 근로소득금액 자체는 그대로
    assert mixed.determined_tax > base.determined_tax


def test_earned_income_credit_is_prorated_to_earned_share() -> None:
    r = _calc(30_000_000, income={"annual_earned_income": 50_000_000})
    comprehensive = r.earned_income_amount + 30_000_000
    earned_tax = truncate_won(Decimal(r.calculated_tax) * r.earned_income_amount / comprehensive)
    eic = next(c for c in r.tax_credits if c.key == "earned_income_credit")
    assert eic.applied_amount == earned_tax
    assert "근로소득 비율" in eic.description


def test_no_earned_income_excludes_earned_only_items() -> None:
    r = _calc(
        40_000_000,
        income={"annual_earned_income": 0},
        deductions={
            "national_pension": 2_000_000,  # 연금보험료공제는 모든 종합소득자
            "health_insurance": 2_000_000,  # 근로소득자만
            "card": {"credit": 30_000_000},  # 근로소득자만
        },
        credits={
            "insurance_general": 1_000_000,  # 근로소득자만
            "medical": {"specific": 3_000_000},  # 근로소득자만
            "donations": {"hometown": 100_000},  # 모든 종합소득자
        },
    )
    keys = {x.key: x for x in r.income_deductions}
    assert keys["pension_insurance"].amount == 2_000_000
    special = keys["special"]
    assert special.amount == 0
    other = keys["other"]
    card = next(c for c in other.children if c.key == "other.card")
    assert card.amount == 0 and "근로소득" in card.description
    assert _credit(r, "earned_income_credit") == 0
    assert _credit(r, "donation.statutory") == 90_909
    # 표준세액공제: 근로소득이 없으면 7만원
    assert r.applied_method == "standard"
    assert _credit(r, "standard_credit") == 70_000


def test_pension_account_rate_uses_comprehensive_income_threshold() -> None:
    # 총급여 5,000만(15% 구간)이지만 사업소득 1,000만이 더해져 종합소득금액 4,500만 초과 → 12%
    only_earned = _calc(income={"annual_earned_income": 50_000_000}, credits={"irp": 1_000_000})
    assert _credit(only_earned, "pension_account_credit") == 150_000
    mixed = _calc(
        10_000_000, income={"annual_earned_income": 50_000_000}, credits={"irp": 1_000_000}
    )
    assert _credit(mixed, "pension_account_credit") == 120_000
    small = _calc(
        1_000_000, income={"annual_earned_income": 50_000_000}, credits={"irp": 1_000_000}
    )
    assert _credit(small, "pension_account_credit") == 150_000  # 종합소득금액 3,825만


def test_business_loss_offsets_earned_income_with_zero_floor() -> None:
    loss = _calc(-10_000_000, income={"annual_earned_income": 50_000_000})
    base = _calc(income={"annual_earned_income": 50_000_000})
    assert loss.tax_base == max(base.tax_base - 10_000_000, 0)
    huge_loss = _calc(-100_000_000, income={"annual_earned_income": 50_000_000})
    assert huge_loss.tax_base == 0
    assert huge_loss.determined_tax == 0


def test_female_deduction_uses_comprehensive_income() -> None:
    # 근로소득금액 3천만 이하라도 종합소득금액이 3천만 초과면 부녀자공제 불가
    kw: dict[str, Any] = {
        "income": {"annual_earned_income": 30_000_000},
        "taxpayer": {"is_female": True, "is_married": True},
    }
    personal = lambda r: r.income_deductions[0].amount  # noqa: E731
    assert personal(_calc(**kw)) == 2_000_000
    assert personal(_calc(20_000_000, **kw)) == 1_500_000
