"""자녀세액공제 (소득세법 제59조의2)."""

from app.tax.eligibility import Eligibility
from app.tax.result import AppliedUnit, BreakdownItem
from app.tax.rules.base import TaxRules


def _child_amount(count: int, rules: TaxRules) -> int:
    c = rules.child_credit
    if count <= 0:
        return 0
    if count == 1:
        return c.first_child
    return c.first_child + c.second_child + (count - 2) * c.third_plus_child


def _birth_amount(order: int, rules: TaxRules) -> int:
    c = rules.child_credit
    if order == 1:
        return c.birth_first
    if order == 2:
        return c.birth_second
    return c.birth_third_plus


def child_credit(eligibility: Eligibility, rules: TaxRules) -> BreakdownItem:
    c = rules.child_credit
    count = eligibility.child_credit_count
    general = BreakdownItem(
        key="child_credit.general",
        label=f"자녀 ({c.min_age}세 이상)",
        applied_unit=AppliedUnit.COUNT,
        applied_amount=count,
        amount=_child_amount(count, rules),
        description=(
            f"{count}명: 첫째 {c.first_child:,}원, 둘째 {c.second_child:,}원, "
            f"셋째 이후 1명당 {c.third_plus_child:,}원"
            if count
            else "해당 없음"
        ),
    )
    births = [p for p in eligibility.basic_persons if p.birth_order is not None]
    birth_children = tuple(
        BreakdownItem(
            key=f"child_credit.birth.{i}",
            label=f"{p.label} ({p.birth_order}째)",
            applied_unit=AppliedUnit.COUNT,
            applied_amount=1,
            amount=_birth_amount(p.birth_order or 1, rules),
        )
        for i, p in enumerate(births)
    )
    birth = BreakdownItem(
        key="child_credit.birth",
        label="출산·입양",
        applied_unit=AppliedUnit.COUNT,
        applied_amount=len(births),
        amount=sum(x.amount for x in birth_children),
        description=(
            f"첫째 {c.birth_first:,}원, 둘째 {c.birth_second:,}원, "
            f"셋째 이상 {c.birth_third_plus:,}원"
            if births
            else "해당 없음"
        ),
        children=birth_children,
    )
    return BreakdownItem(
        key="child_credit",
        label="자녀세액공제",
        applied_unit=AppliedUnit.COUNT,
        applied_amount=count + len(births),
        amount=general.amount + birth.amount,
        children=(general, birth),
    )
