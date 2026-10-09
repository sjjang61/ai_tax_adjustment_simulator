"""속성 기반 테스트: 단조성·불변식 검증 (Hypothesis)."""

from typing import Any

from hypothesis import given, settings
from hypothesis import strategies as st

from app.tax.engine import calculate
from app.tax.rules import get_rules
from tests.factories import make_input

RULES = get_rules(2025)

salary = st.integers(min_value=0, max_value=1_500_000_000)
amount = st.integers(min_value=0, max_value=50_000_000)
delta = st.integers(min_value=1, max_value=20_000_000)


def _determined(gross: int, **override: Any) -> int:
    inp = make_input(income={"annual_earned_income": gross}, **override)
    return calculate(inp, RULES).determined_tax


@settings(max_examples=200, deadline=None)
@given(gross=salary, inc=delta)
def test_higher_salary_never_lowers_tax(gross: int, inc: int) -> None:
    assert _determined(gross + inc) >= _determined(gross)


@settings(max_examples=150, deadline=None)
@given(
    gross=salary,
    field=st.sampled_from(["national_pension", "health_insurance", "venture_direct"]),
    base=amount,
    inc=delta,
)
def test_more_income_deduction_never_raises_tax(
    gross: int, field: str, base: int, inc: int
) -> None:
    low = _determined(gross, deductions={field: base})
    high = _determined(gross, deductions={field: base + inc})
    assert high <= low


@settings(max_examples=150, deadline=None)
@given(
    gross=salary,
    field=st.sampled_from(["pension_savings", "irp", "insurance_general"]),
    base=amount,
    inc=delta,
)
def test_more_tax_credit_input_never_raises_tax(
    gross: int, field: str, base: int, inc: int
) -> None:
    low = _determined(gross, credits={field: base})
    high = _determined(gross, credits={field: base + inc})
    assert high <= low


@settings(max_examples=100, deadline=None)
@given(gross=salary, credit=amount, debit=amount, market=amount)
def test_more_card_usage_never_raises_tax(gross: int, credit: int, debit: int, market: int) -> None:
    low = _determined(gross, deductions={"card": {"credit": credit, "debit_cash": debit}})
    high = _determined(
        gross,
        deductions={"card": {"credit": credit, "debit_cash": debit, "traditional_market": market}},
    )
    assert high <= low


@settings(max_examples=200, deadline=None)
@given(gross=salary, rent=amount, medical=amount, prepaid=amount)
def test_invariants(gross: int, rent: int, medical: int, prepaid: int) -> None:
    inp = make_input(
        income={"annual_earned_income": gross},
        taxpayer={"is_homeless": True},
        prepaid_tax={"withholding": prepaid},
        credits={"monthly_rent": rent, "medical": {"specific": medical}},
    )
    r = calculate(inp, RULES)
    assert r.determined_tax >= 0
    assert r.total_tax_credit <= r.calculated_tax
    assert r.tax_base <= r.earned_income_amount
    assert r.determined_tax == min(m.determined_tax for m in r.method_comparison)
    assert abs(r.balance_due - (r.determined_tax - r.prepaid_tax)) < 10


@settings(max_examples=100, deadline=None)
@given(gross=salary, base=st.integers(min_value=0, max_value=100_000_000), inc=delta)
def test_more_national_growth_fund_never_raises_tax_2026(gross: int, base: int, inc: int) -> None:
    rules = get_rules(2026)

    def determined(amount: int) -> int:
        inp = make_input(
            tax_year=2026,
            income={"annual_earned_income": gross},
            deductions={"national_growth_fund": amount},
        )
        return calculate(inp, rules).determined_tax

    assert determined(base + inc) <= determined(base)
