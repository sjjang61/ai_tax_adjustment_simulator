"""국민참여형 국민성장펀드 투자 소득공제 (2026년 귀속 신설, 조특법 개정 2026.4.23. 국회 통과).

전용계좌로 3년 이상 투자한 금액에 구간별 공제율을 누적 적용하고 최대 공제액으로 제한한다.
소득공제 종합한도 대상 여부는 규칙 값(included_in_aggregate_limit)을 따른다.
"""

from app.tax.result import BreakdownItem
from app.tax.rules.base import TaxRules
from app.tax.tiers import describe_tiers, tiered_amount

KEY = "other.national_growth_fund"
LABEL = "국민성장펀드"


def national_growth_fund_deduction(investment: int, rules: TaxRules) -> BreakdownItem:
    r = rules.national_growth_fund
    if r is None:
        return BreakdownItem(
            key=KEY,
            label=LABEL,
            applied_amount=investment,
            amount=0,
            limited=investment > 0,
            description=f"{rules.tax_year}년 귀속에는 국민성장펀드 소득공제가 없습니다."
            if investment
            else "",
        )
    tiers = [t for t in r.tiers if t.rate > 0]
    raw = tiered_amount(investment, r.tiers)
    amount = min(raw, r.max_deduction)
    # 공제율 0% 구간(7천만원 초과분)에 투자액이 있거나 최대 공제액에 걸리면 한도 적용으로 표시
    zero_rate_start = max((t.upper or 0) for t in tiers) if tiers else 0
    limited = amount < raw or investment > zero_rate_start
    return BreakdownItem(
        key=KEY,
        label=LABEL,
        applied_amount=investment,
        amount=amount,
        limited=limited,
        description=(
            f"{describe_tiers(tiers)} (최대 {r.max_deduction:,}원, "
            f"{r.min_holding_years}년 이상 보유 요건"
            + (", 소득공제 종합한도 포함" if r.included_in_aggregate_limit else "")
            + ")"
            if investment
            else ""
        ),
    )
