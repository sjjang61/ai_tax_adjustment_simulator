"""근로소득세액공제 (소득세법 제59조)."""

from decimal import Decimal

from app.tax.money import apply_rate, format_percent, truncate_won
from app.tax.result import BreakdownItem
from app.tax.rules.base import TaxRules


def earned_income_credit_limit(gross_salary: int, rules: TaxRules) -> int:
    """총급여 구간별 공제 한도 (제59조 제2항)."""
    for tier in rules.earned_income_credit.limit_tiers:
        if tier.upper is None or gross_salary <= tier.upper:
            # 감액분 원 미만 절사 후 하한 적용
            reduced = tier.base - truncate_won(
                Decimal(max(gross_salary - tier.lower, 0)) * tier.reduction_rate
            )
            return max(reduced, tier.floor)
    raise AssertionError("limit_tiers must end with an open-ended tier")  # pragma: no cover


def earned_income_credit(calculated_tax: int, gross_salary: int, rules: TaxRules) -> BreakdownItem:
    r = rules.earned_income_credit
    if calculated_tax <= r.tax_threshold:
        raw = apply_rate(calculated_tax, r.low_rate)
        formula = f"산출세액 × {format_percent(r.low_rate)}"
    else:
        # 130만원까지 55%, 초과분 30% — 구간별 금액을 합산한 뒤 원 미만 절사
        raw = truncate_won(
            Decimal(r.tax_threshold) * r.low_rate
            + Decimal(calculated_tax - r.tax_threshold) * r.high_rate
        )
        formula = (
            f"{r.tax_threshold:,}원 × {format_percent(r.low_rate)} + 초과분 × "
            f"{format_percent(r.high_rate)}"
        )
    limit = earned_income_credit_limit(gross_salary, rules)
    amount = min(raw, limit)
    return BreakdownItem(
        key="earned_income_credit",
        label="근로소득세액공제",
        applied_amount=calculated_tax,
        amount=amount,
        limited=amount < raw,
        description=f"{formula}, 총급여 기준 한도 {limit:,}원",
    )
