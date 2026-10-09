"""국민참여형 국민성장펀드 소득공제 (2026년 귀속 신설)."""

import pytest

from app.tax.deductions.national_growth_fund import national_growth_fund_deduction
from app.tax.eligibility import evaluate
from app.tax.engine import calculate
from app.tax.rules import get_rules
from tests.factories import make_input

RULES_2026 = get_rules(2026)


@pytest.mark.parametrize(
    ("investment", "expected", "limited"),
    [
        (0, 0, False),
        (29_999_999, 11_999_999, False),  # 40%: 11,999,999.6 → 절사
        (30_000_000, 12_000_000, False),
        (30_000_001, 12_000_000, False),  # 1원 × 20% = 0.2 → 절사
        (50_000_000, 16_000_000, False),  # 1,200만 + 2,000만 × 20%
        (50_000_010, 16_000_001, False),  # 10원 × 10%
        (70_000_000, 18_000_000, False),  # 1,600만 + 2,000만 × 10% = 최대 1,800만
        (70_000_001, 18_000_000, True),  # 7천만원 초과분은 공제 없음
        (200_000_000, 18_000_000, True),
    ],
)
def test_tiers_and_max(investment: int, expected: int, limited: bool) -> None:
    item = national_growth_fund_deduction(investment, RULES_2026)
    assert item.amount == expected
    assert item.limited is limited
    assert item.key == "other.national_growth_fund"


def test_not_available_in_2025() -> None:
    item = national_growth_fund_deduction(10_000_000, get_rules(2025))
    assert item.amount == 0
    assert item.limited
    assert get_rules(2025).national_growth_fund is None


def test_rules_2026_values() -> None:
    r = RULES_2026.national_growth_fund
    assert r is not None
    assert r.max_deduction == 18_000_000
    assert r.min_holding_years == 3
    assert r.included_in_aggregate_limit is True


def test_warnings() -> None:
    inp_2025 = make_input(deductions={"national_growth_fund": 10_000_000})
    codes_2025 = {w.code for w in evaluate(inp_2025, get_rules(2025)).warnings}
    assert "national_growth_fund_unavailable" in codes_2025

    inp_2026 = make_input(tax_year=2026, deductions={"national_growth_fund": 10_000_000})
    codes_2026 = {w.code for w in evaluate(inp_2026, RULES_2026).warnings}
    assert "national_growth_fund_holding_period" in codes_2026
    assert "national_growth_fund_unavailable" not in codes_2026


def test_engine_includes_fund_in_other_deductions_and_aggregate_limit() -> None:
    inp = make_input(
        tax_year=2026,
        income={"annual_earned_income": 150_000_000},
        deductions={
            "national_growth_fund": 70_000_000,  # 1,800만원
            "long_term_mortgage_interest": 8_000_000,
            "mortgage_type": "fixed_and_non_deferred_15y",
        },
    )
    r = calculate(inp, RULES_2026)
    other = next(x for x in r.income_deductions if x.key == "other")
    fund = next(c for c in other.children if c.key == "other.national_growth_fund")
    assert fund.amount == 18_000_000
    aggregate = next(x for x in r.income_deductions if x.key == "aggregate_limit")
    # 1,800만 + 장기주택저당 800만 = 2,600만 → 종합한도 2,500만 초과 100만 차감
    assert aggregate.amount == -1_000_000


def test_engine_ignores_fund_in_2025() -> None:
    base = calculate(make_input(), get_rules(2025))
    with_fund = calculate(
        make_input(deductions={"national_growth_fund": 30_000_000}), get_rules(2025)
    )
    assert with_fund.determined_tax == base.determined_tax
