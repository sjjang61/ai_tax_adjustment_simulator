"""연금보험료공제(소득세법 제51조의3)와 특별소득공제 중 보험료공제(제52조 제1항)."""

from app.tax.inputs import IncomeDeductionInput
from app.tax.result import BreakdownItem


def pension_insurance_deduction(d: IncomeDeductionInput) -> BreakdownItem:
    return BreakdownItem(
        key="pension_insurance",
        label="연금보험료공제",
        applied_amount=d.national_pension,
        amount=d.national_pension,
        description="국민연금 등 공적연금 근로자 부담분 전액 공제",
    )


def social_insurance_deduction(d: IncomeDeductionInput) -> BreakdownItem:
    total = d.health_insurance + d.employment_insurance
    return BreakdownItem(
        key="special.social_insurance",
        label="건강·고용보험료",
        applied_amount=total,
        amount=total,
        description="근로자 부담분 전액 공제 (특별소득공제)",
        children=(
            BreakdownItem(
                key="special.social_insurance.health",
                label="건강보험료(장기요양 포함)",
                applied_amount=d.health_insurance,
                amount=d.health_insurance,
            ),
            BreakdownItem(
                key="special.social_insurance.employment",
                label="고용보험료",
                applied_amount=d.employment_insurance,
                amount=d.employment_insurance,
            ),
        ),
    )
