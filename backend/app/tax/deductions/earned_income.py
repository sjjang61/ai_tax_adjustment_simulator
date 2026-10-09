"""근로소득공제 (소득세법 제47조)."""

from decimal import Decimal

from app.tax.money import format_percent, truncate_won
from app.tax.result import BreakdownItem
from app.tax.rules.base import TaxRules


def earned_income_deduction(gross_salary: int, rules: TaxRules) -> BreakdownItem:
    r = rules.earned_income_deduction
    raw = 0
    description = "총급여가 없어 공제액이 없습니다."
    for b in r.brackets:
        if b.upper is None or gross_salary <= b.upper:
            # 원 미만 절사 (소득세법상 공제액 산정 시 원 단위 미만 버림)
            raw = b.base_amount + truncate_won(Decimal(gross_salary - b.lower) * b.rate)
            if gross_salary > 0:
                description = (
                    f"{b.base_amount:,}원 + ({b.lower:,}원 초과분 × {format_percent(b.rate)})"
                    if b.lower
                    else f"총급여 × {format_percent(b.rate)}"
                )
            break
    limited = raw > r.max_deduction
    amount = min(raw, r.max_deduction)
    if limited:
        description += f" → 한도 {r.max_deduction:,}원 적용"
    return BreakdownItem(
        key="earned_income_deduction",
        label="근로소득공제",
        applied_amount=gross_salary,
        amount=amount,
        limited=limited,
        description=description,
    )
