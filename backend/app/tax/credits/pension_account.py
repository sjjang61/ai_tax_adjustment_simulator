"""연금계좌세액공제 (소득세법 제59조의3)."""

from app.tax.money import apply_rate, format_percent
from app.tax.result import BreakdownItem
from app.tax.rules.base import TaxRules


def pension_account_credit(
    pension_savings: int, irp: int, gross_salary: int, rules: TaxRules
) -> BreakdownItem:
    r = rules.pension_account
    savings_eligible = min(pension_savings, r.savings_limit)
    total_eligible = min(savings_eligible + irp, r.combined_limit)
    rate = r.high_rate if gross_salary <= r.high_rate_gross_salary_limit else r.low_rate
    amount = apply_rate(total_eligible, rate)
    paid = pension_savings + irp
    return BreakdownItem(
        key="pension_account_credit",
        label="연금계좌세액공제",
        applied_amount=paid,
        amount=amount,
        limited=total_eligible < paid,
        description=(
            f"공제대상 {total_eligible:,}원 (연금저축 한도 {r.savings_limit:,}원, "
            f"IRP 합산 한도 {r.combined_limit:,}원) × {format_percent(rate)}"
            if paid
            else ""
        ),
    )
