"""교육비 세액공제 (소득세법 제59조의4 제3항)."""

from collections.abc import Sequence

from app.tax.inputs import EducationExpense, EducationKind
from app.tax.money import apply_rate, format_percent
from app.tax.result import BreakdownItem
from app.tax.rules.base import TaxRules

_LABELS = {
    EducationKind.SELF: "본인",
    EducationKind.PRESCHOOL: "취학전 아동",
    EducationKind.SCHOOL: "초·중·고",
    EducationKind.UNIVERSITY: "대학생",
    EducationKind.DISABLED_SPECIAL: "장애인 특수교육비",
}


def _limit(kind: EducationKind, rules: TaxRules) -> int | None:
    r = rules.education_credit
    match kind:
        case EducationKind.PRESCHOOL:
            return r.preschool_limit
        case EducationKind.SCHOOL:
            return r.school_limit
        case EducationKind.UNIVERSITY:
            return r.university_limit
        case _:
            return None  # 본인·장애인 특수교육비는 한도 없음


def education_credit(items: Sequence[EducationExpense], rules: TaxRules) -> BreakdownItem:
    r = rules.education_credit
    children: list[BreakdownItem] = []
    for i, item in enumerate(items):
        limit = _limit(item.kind, rules)
        base = item.amount if limit is None else min(item.amount, limit)
        children.append(
            BreakdownItem(
                key=f"education_credit.{i}",
                label=item.label or _LABELS[item.kind],
                applied_amount=item.amount,
                amount=apply_rate(base, r.rate),
                limited=base < item.amount,
                description=(
                    f"{'한도 없음' if limit is None else f'1인당 한도 {limit:,}원'} × "
                    f"{format_percent(r.rate)}"
                ),
            )
        )
    return BreakdownItem(
        key="education_credit",
        label="교육비",
        applied_amount=sum(x.amount for x in items),
        amount=sum(x.amount for x in children),
        limited=any(x.limited for x in children),
        children=tuple(children),
    )
