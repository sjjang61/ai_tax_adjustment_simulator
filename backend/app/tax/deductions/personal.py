"""인적공제: 기본공제(소득세법 제50조) + 추가공제(제51조)."""

from app.tax.eligibility import Eligibility
from app.tax.result import AppliedUnit, BreakdownItem
from app.tax.rules.base import TaxRules


def personal_deduction(eligibility: Eligibility, rules: TaxRules) -> BreakdownItem:
    p = rules.personal
    basic_persons = eligibility.basic_persons
    basic_count = len(basic_persons)
    basic = BreakdownItem(
        key="personal_deduction.basic",
        label="기본공제",
        applied_unit=AppliedUnit.COUNT,
        applied_amount=basic_count,
        amount=basic_count * p.basic_per_person,
        description=(
            f"{basic_count}명 × {p.basic_per_person:,}원 ("
            + ", ".join(x.label for x in basic_persons)
            + ")"
        ),
    )

    additional: list[BreakdownItem] = []
    elderly = [x for x in basic_persons if x.elderly]
    if elderly:
        additional.append(
            BreakdownItem(
                key="personal_deduction.additional.elderly",
                label="경로우대",
                applied_unit=AppliedUnit.COUNT,
                applied_amount=len(elderly),
                amount=len(elderly) * p.elderly_additional,
                description=f"{p.elderly_min_age}세 이상 {len(elderly)}명 × "
                f"{p.elderly_additional:,}원 ({', '.join(x.label for x in elderly)})",
            )
        )
    disabled = [x for x in basic_persons if x.disabled]
    if disabled:
        additional.append(
            BreakdownItem(
                key="personal_deduction.additional.disabled",
                label="장애인",
                applied_unit=AppliedUnit.COUNT,
                applied_amount=len(disabled),
                amount=len(disabled) * p.disabled_additional,
                description=f"{len(disabled)}명 × {p.disabled_additional:,}원 "
                f"({', '.join(x.label for x in disabled)})",
            )
        )
    if eligibility.female_deduction:
        additional.append(
            BreakdownItem(
                key="personal_deduction.additional.female",
                label="부녀자",
                applied_unit=AppliedUnit.COUNT,
                applied_amount=1,
                amount=p.female_additional,
                description=f"근로소득금액 {p.female_earned_income_limit:,}원 이하 여성",
            )
        )
    if eligibility.single_parent_deduction:
        additional.append(
            BreakdownItem(
                key="personal_deduction.additional.single_parent",
                label="한부모",
                applied_unit=AppliedUnit.COUNT,
                applied_amount=1,
                amount=p.single_parent_additional,
                description="배우자 없이 기본공제 대상 자녀가 있음",
            )
        )
    additional_total = sum(x.amount for x in additional)
    additional_item = BreakdownItem(
        key="personal_deduction.additional",
        label="추가공제",
        applied_unit=AppliedUnit.COUNT,
        applied_amount=len(additional),
        amount=additional_total,
        description="해당 없음" if not additional else "",
        children=tuple(additional),
    )
    return BreakdownItem(
        key="personal_deduction",
        label="인적공제",
        applied_unit=AppliedUnit.COUNT,
        applied_amount=basic_count,
        amount=basic.amount + additional_total,
        children=(basic, additional_item),
    )
