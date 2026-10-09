"""보험료 세액공제 (소득세법 제59조의4 제1항)."""

from app.tax.money import apply_rate, format_percent
from app.tax.result import BreakdownItem
from app.tax.rules.base import TaxRules


def insurance_credit(general: int, disabled: int, rules: TaxRules) -> BreakdownItem:
    r = rules.insurance_credit
    general_base = min(general, r.general_limit)
    disabled_base = min(disabled, r.disabled_limit)
    children = (
        BreakdownItem(
            key="insurance_credit.general",
            label="보장성보험",
            applied_amount=general,
            amount=apply_rate(general_base, r.general_rate),
            limited=general_base < general,
            description=f"min(납입액, {r.general_limit:,}원) × {format_percent(r.general_rate)}",
        ),
        BreakdownItem(
            key="insurance_credit.disabled",
            label="장애인전용 보장성보험",
            applied_amount=disabled,
            amount=apply_rate(disabled_base, r.disabled_rate),
            limited=disabled_base < disabled,
            description=f"min(납입액, {r.disabled_limit:,}원) × {format_percent(r.disabled_rate)}",
        ),
    )
    return BreakdownItem(
        key="insurance_credit",
        label="보험료",
        applied_amount=general + disabled,
        amount=sum(x.amount for x in children),
        limited=any(x.limited for x in children),
        children=children,
    )
