"""신용카드 등 소득공제 (조특법 제126조의2)."""

from typing import Any

import pytest

from app.tax.deductions.card import card_deduction
from app.tax.inputs import CardUsage
from app.tax.rules import get_rules

RULES = get_rules(2025)
GROSS = 40_000_000  # 최저사용금액 10,000,000원


def _card(gross: int = GROSS, children: int = 0, year: int = 2025, **usage: Any) -> int:
    return card_deduction(CardUsage(**usage), gross, children, get_rules(year)).amount


def test_zero_usage() -> None:
    item = card_deduction(CardUsage(), GROSS, 0, RULES)
    assert item.amount == 0
    assert item.description == ""


@pytest.mark.parametrize(
    ("credit", "expected"),
    [
        (9_999_999, 0),  # 최저사용금액 미달
        (10_000_000, 0),  # 정확히 최저사용금액
        (10_000_001, 0),  # 1원 × 15% = 0.15 → 절사
        (10_000_007, 1),
        (20_000_000, 1_500_000),
    ],
)
def test_minimum_usage_boundary(credit: int, expected: int) -> None:
    assert _card(credit=credit) == expected


def test_below_minimum_description() -> None:
    item = card_deduction(CardUsage(credit=5_000_000), GROSS, 0, RULES)
    assert "최저사용금액" in item.description


def test_minimum_usage_deducted_from_credit_first() -> None:
    # 신용카드 5백만 전액 + 체크카드 5백만이 최저사용금액으로 차감 → 체크 5백만 × 30%
    assert _card(credit=5_000_000, debit_cash=10_000_000) == 1_500_000


def test_basic_limit() -> None:
    item = card_deduction(CardUsage(credit=40_000_000), GROSS, 0, RULES)
    assert item.amount == 3_000_000
    assert item.limited


def test_additional_deduction_within_pool() -> None:
    # 신용 4.5M + 전통시장 0.8M + 대중교통 0.4M = 5.7M → 기본 3M + 추가 min(2.7M, 1.2M, 3M)
    assert (
        _card(credit=40_000_000, traditional_market=2_000_000, public_transport=1_000_000)
        == 4_200_000
    )


def test_additional_limit() -> None:
    # 전통시장 4M 공제가능 → 추가한도 3M
    assert _card(credit=40_000_000, traditional_market=10_000_000) == 6_000_000


def test_culture_and_sports_count_for_additional() -> None:
    assert _card(credit=40_000_000, culture=2_000_000, sports_facility=1_000_000) == 3_900_000


@pytest.mark.parametrize(
    ("gross", "expected"),
    [
        (70_000_000, 3_000_000),
        (70_000_001, 2_500_000),
    ],
)
def test_basic_limit_salary_boundary(gross: int, expected: int) -> None:
    assert _card(gross=gross, credit=100_000_000) == expected


def test_high_income_additional_limit_and_culture_excluded() -> None:
    gross = 80_000_000  # 최저사용금액 20M
    # 신용 40M → 3M, 전통시장 10M → 4M (추가한도 2M)
    assert _card(gross=gross, credit=40_000_000, traditional_market=10_000_000) == 4_500_000
    # 도서·공연은 신용카드 공제율 15%로, 추가공제 대상 아님
    item = card_deduction(CardUsage(credit=20_000_000, culture=10_000_000), gross, 0, RULES)
    assert item.amount == 1_500_000
    assert [c.key for c in item.children] == ["other.card.credit"]


@pytest.mark.parametrize(
    ("gross", "children", "expected"),
    [
        (50_000_000, 0, 3_000_000),
        (50_000_000, 1, 3_500_000),
        (50_000_000, 2, 4_000_000),
        (50_000_000, 3, 4_000_000),  # 최대 100만원
        (80_000_000, 1, 2_750_000),
        (80_000_000, 3, 3_000_000),  # 최대 50만원
    ],
)
def test_2026_child_basic_limit(gross: int, children: int, expected: int) -> None:
    assert _card(gross=gross, children=children, year=2026, credit=200_000_000) == expected


def test_2025_has_no_child_limit() -> None:
    assert _card(gross=50_000_000, children=2, credit=200_000_000) == 3_000_000
