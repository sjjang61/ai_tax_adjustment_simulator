"""주택자금·벤처투자 소득공제와 소득공제 종합한도."""

from typing import Any

import pytest

from app.tax.deductions.aggregate_limit import aggregate_limit_adjustment
from app.tax.deductions.housing import HousingDeductions, housing_deductions
from app.tax.deductions.venture import venture_deduction
from app.tax.eligibility import evaluate
from app.tax.result import BreakdownItem
from app.tax.rules import get_rules
from tests.factories import make_input

RULES = get_rules(2025)


def _housing(
    include_special: bool = True, homeless: bool = True, gross: int = 50_000_000, **d: Any
) -> HousingDeductions:
    inp = make_input(
        income={"annual_earned_income": gross},
        taxpayer={"is_homeless": homeless},
        deductions=d,
    )
    return housing_deductions(
        inp.deductions, evaluate(inp, RULES), RULES, include_special=include_special
    )


@pytest.mark.parametrize(
    ("repayment", "expected", "limited"),
    [
        (0, 0, False),
        (5_000_000, 2_000_000, False),
        (10_000_000, 4_000_000, False),
        (10_000_003, 4_000_000, True),
        (12_000_000, 4_000_000, True),
    ],
)
def test_rent_loan(repayment: int, expected: int, limited: bool) -> None:
    item = _housing(housing_rent_loan_repayment=repayment).rent_loan
    assert (item.amount, item.limited) == (expected, limited)


@pytest.mark.parametrize(
    ("payment", "expected", "limited"),
    [
        (0, 0, False),
        (2_999_999, 1_199_999, False),
        (3_000_000, 1_200_000, False),
        (3_000_001, 1_200_000, True),
    ],
)
def test_subscription(payment: int, expected: int, limited: bool) -> None:
    item = _housing(housing_subscription=payment).subscription
    assert (item.amount, item.limited) == (expected, limited)


def test_subscription_shares_limit_with_rent_loan() -> None:
    h = _housing(housing_rent_loan_repayment=9_000_000, housing_subscription=3_000_000)
    assert h.rent_loan.amount == 3_600_000
    assert h.subscription.amount == 400_000
    assert h.subscription.limited


def test_subscription_ineligible() -> None:
    h = _housing(homeless=False, housing_subscription=3_000_000)
    assert h.subscription.amount == 0 and h.subscription.limited
    h = _housing(gross=70_000_001, housing_subscription=3_000_000)
    assert h.subscription.amount == 0
    h = _housing(gross=70_000_000, housing_subscription=3_000_000)
    assert h.subscription.amount == 1_200_000


def test_rent_loan_ineligible() -> None:
    h = _housing(homeless=False, housing_rent_loan_repayment=5_000_000)
    assert h.rent_loan.amount == 0 and h.rent_loan.limited


@pytest.mark.parametrize(
    ("mortgage_type", "interest", "expected"),
    [
        ("fixed_and_non_deferred_15y", 25_000_000, 20_000_000),
        ("fixed_or_non_deferred_15y", 18_000_000, 18_000_000),
        ("fixed_or_non_deferred_15y", 18_000_001, 18_000_000),
        ("other_15y", 9_000_000, 8_000_000),
        ("fixed_or_non_deferred_10y", 5_000_000, 5_000_000),
    ],
)
def test_mortgage_limits(mortgage_type: str, interest: int, expected: int) -> None:
    h = _housing(long_term_mortgage_interest=interest, mortgage_type=mortgage_type)
    assert h.mortgage.amount == expected
    assert h.mortgage.limited is (interest > expected)


def test_mortgage_combined_with_rent_loan_and_subscription() -> None:
    h = _housing(
        housing_rent_loan_repayment=5_000_000,  # 2,000,000
        long_term_mortgage_interest=7_000_000,
        mortgage_type="other_15y",  # 한도 8,000,000
        housing_subscription=3_000_000,
    )
    assert h.rent_loan.amount == 2_000_000
    assert h.mortgage.amount == 6_000_000
    assert h.subscription.amount == 0


def test_mortgage_without_type_is_zero() -> None:
    assert _housing(long_term_mortgage_interest=5_000_000).mortgage.amount == 0


def test_standard_method_excludes_special_housing() -> None:
    h = _housing(
        include_special=False,
        housing_rent_loan_repayment=5_000_000,
        long_term_mortgage_interest=5_000_000,
        mortgage_type="other_15y",
        housing_subscription=1_000_000,
    )
    assert h.rent_loan.amount == 0
    assert h.mortgage.amount == 0
    assert "표준세액공제" in h.rent_loan.description
    assert h.subscription.amount == 400_000


@pytest.mark.parametrize(
    ("direct", "fund", "income", "expected"),
    [
        (0, 0, 50_000_000, 0),
        (30_000_000, 0, 100_000_000, 30_000_000),
        (50_000_000, 0, 100_000_000, 44_000_000),
        (60_000_000, 0, 100_000_000, 47_000_000),
        (60_000_000, 0, 40_000_000, 20_000_000),  # 근로소득금액의 50%
        (0, 10_000_000, 40_000_000, 1_000_000),
    ],
)
def test_venture(direct: int, fund: int, income: int, expected: int) -> None:
    v = venture_deduction(direct, fund, income, RULES)
    assert v.item.amount == expected


def test_venture_limit_cuts_fund_first() -> None:
    v = venture_deduction(30_000_000, 10_000_000, 61_000_000, RULES)  # 한도 30.5M
    assert (v.direct_amount, v.fund_amount) == (30_000_000, 500_000)
    assert v.item.limited


def _item(amount: int) -> BreakdownItem:
    return BreakdownItem(key="x", label="x", applied_amount=amount, amount=amount)


@pytest.mark.parametrize(
    ("amounts", "fund", "excess"),
    [
        ([20_000_000, 4_000_000], 999_999, 0),
        ([20_000_000, 4_000_000], 1_000_000, 0),
        ([20_000_000, 4_000_000], 1_000_001, 1),
        ([24_000_000, 3_000_000], 0, 2_000_000),
    ],
)
def test_aggregate_limit(amounts: list[int], fund: int, excess: int) -> None:
    adj = aggregate_limit_adjustment([_item(a) for a in amounts], fund, RULES)
    assert adj.amount == -excess
    assert adj.limited is (excess > 0)
