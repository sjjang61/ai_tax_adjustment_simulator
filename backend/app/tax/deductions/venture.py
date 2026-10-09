"""벤처기업 등 투자 소득공제 (조특법 제16조)."""

from dataclasses import dataclass

from app.tax.money import apply_rate, format_percent
from app.tax.result import BreakdownItem
from app.tax.rules.base import TaxRules
from app.tax.tiers import describe_tiers, tiered_amount


@dataclass(frozen=True)
class VentureDeduction:
    item: BreakdownItem
    fund_amount: int  # 종합한도 대상(간접투자분) 공제액
    direct_amount: int  # 종합한도 제외(직접투자분) 공제액


def venture_deduction(
    direct: int, fund: int, earned_income_amount: int, rules: TaxRules
) -> VentureDeduction:
    v = rules.venture
    direct_raw = tiered_amount(direct, v.direct_tiers)
    fund_raw = apply_rate(fund, v.fund_rate)
    # 한도: 종합소득금액(근로소득금액) × 50%, 원 미만 절사
    limit = apply_rate(earned_income_amount, v.income_limit_rate)
    raw = direct_raw + fund_raw
    total = min(raw, limit)
    # 한도 초과 시 간접투자(종합한도 대상)분부터 줄여, 직접투자분을 최대한 보존한다.
    direct_amount = min(direct_raw, total)
    fund_amount = total - direct_amount

    children: list[BreakdownItem] = []
    if direct:
        children.append(
            BreakdownItem(
                key="other.venture.direct",
                label="벤처기업 등 직접투자",
                applied_amount=direct,
                amount=direct_amount,
                limited=direct_amount < direct_raw,
                description=f"{describe_tiers(v.direct_tiers)} (소득공제 종합한도 제외)",
            )
        )
    if fund:
        children.append(
            BreakdownItem(
                key="other.venture.fund",
                label="벤처투자조합 등 간접투자",
                applied_amount=fund,
                amount=fund_amount,
                limited=fund_amount < fund_raw,
                description=f"투자액 × {format_percent(v.fund_rate)}",
            )
        )
    item = BreakdownItem(
        key="other.venture",
        label="벤처투자 등",
        applied_amount=direct + fund,
        amount=total,
        limited=total < raw,
        description=(
            f"한도: 근로소득금액 × {format_percent(v.income_limit_rate)} = {limit:,}원"
            if direct or fund
            else ""
        ),
        children=tuple(children),
    )
    return VentureDeduction(item=item, fund_amount=fund_amount, direct_amount=direct_amount)
