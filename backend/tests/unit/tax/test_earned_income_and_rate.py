"""근로소득공제(소득세법 제47조)와 기본세율(제55조)."""

from itertools import pairwise

import pytest

from app.tax.deductions.earned_income import earned_income_deduction
from app.tax.rules import get_rules
from app.tax.tax_rate import calculate_tax

RULES = get_rules(2025)


@pytest.mark.parametrize(
    ("gross", "expected"),
    [
        (0, 0),
        (4_999_999, 3_499_999),  # 70%: 3,499,999.3 → 절사
        (5_000_000, 3_500_000),
        (5_000_001, 3_500_000),  # 350만 + 1 × 40% = 0.4 → 절사
        (15_000_000, 7_500_000),
        (15_000_001, 7_500_000),
        (45_000_000, 12_000_000),
        (45_000_001, 12_000_000),
        (57_600_000, 12_630_000),
        (100_000_000, 14_750_000),
        (100_000_001, 14_750_000),
        (362_499_999, 19_999_999),
    ],
)
def test_earned_income_deduction_boundaries(gross: int, expected: int) -> None:
    item = earned_income_deduction(gross, RULES)
    assert item.amount == expected
    assert item.limited is False


@pytest.mark.parametrize(
    ("gross", "limited"),
    [
        (362_500_000, False),  # 정확히 한도
        (362_500_049, False),  # 초과분 0.98원 → 절사 후 한도와 같음
        (362_500_050, True),
        (1_000_000_000, True),
    ],
)
def test_earned_income_deduction_limit(gross: int, limited: bool) -> None:
    item = earned_income_deduction(gross, RULES)
    assert item.amount == 20_000_000
    assert item.limited is limited


@pytest.mark.parametrize(
    ("tax_base", "expected"),
    [
        (0, 0),
        (13_999_999, 839_999),
        (14_000_000, 840_000),
        (14_000_001, 840_000),  # 0.15 → 절사
        (50_000_000, 6_240_000),
        (50_000_001, 6_240_000),
        (88_000_000, 15_360_000),
        (150_000_000, 37_060_000),
        (300_000_000, 94_060_000),
        (500_000_000, 174_060_000),
        (1_000_000_000, 384_060_000),
        (1_000_000_001, 384_060_000),
    ],
)
def test_calculated_tax_boundaries(tax_base: int, expected: int) -> None:
    assert calculate_tax(tax_base, RULES).amount == expected


def test_tax_brackets_are_continuous() -> None:
    """누진공제액 방식이 구간 경계에서 연속인지 검증한다 (규칙 값 정합성)."""
    brackets = RULES.tax_rate_brackets
    for lower, upper in pairwise(brackets):
        assert lower.upper is not None
        boundary = lower.upper
        assert (
            boundary * lower.rate - lower.progressive_deduction
            == boundary * upper.rate - upper.progressive_deduction
        )
