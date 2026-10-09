"""월세(조특법 제95조의2)·표준(소득세법 제59조의4 제9항)·결혼(조특법 제92조) 세액공제."""

from app.tax.money import apply_rate, format_percent
from app.tax.result import AppliedUnit, BreakdownItem
from app.tax.rules.base import TaxRules


def monthly_rent_credit(
    rent: int, gross_salary: int, eligible: bool, rules: TaxRules
) -> BreakdownItem:
    r = rules.rent_credit
    if not eligible:
        return BreakdownItem(
            key="monthly_rent_credit",
            label="월세",
            applied_amount=rent,
            amount=0,
            limited=rent > 0,
            description="무주택·총급여 요건 미충족" if rent else "",
        )
    base = min(rent, r.payment_limit)
    rate = r.high_rate if gross_salary <= r.high_rate_gross_salary_limit else r.low_rate
    return BreakdownItem(
        key="monthly_rent_credit",
        label="월세",
        applied_amount=rent,
        amount=apply_rate(base, rate),
        limited=base < rent,
        description=f"min(월세, {r.payment_limit:,}원) × {format_percent(rate)}" if rent else "",
    )


def standard_credit(rules: TaxRules) -> BreakdownItem:
    return BreakdownItem(
        key="standard_credit",
        label="표준세액공제",
        applied_unit=AppliedUnit.COUNT,
        applied_amount=0,
        amount=rules.standard_credit,
        description="특별소득공제·특별세액공제·월세세액공제를 신청하지 않은 근로자",
    )


def marriage_credit(registered_this_year: bool, rules: TaxRules) -> BreakdownItem:
    amount = rules.marriage_credit if registered_this_year and rules.marriage_credit else 0
    return BreakdownItem(
        key="marriage_credit",
        label="결혼세액공제",
        applied_unit=AppliedUnit.COUNT,
        applied_amount=1 if registered_this_year else 0,
        amount=amount,
        description="혼인신고한 해 1회" if amount else "",
    )
