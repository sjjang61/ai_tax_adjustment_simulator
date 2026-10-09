"""소득공제 종합한도 (조특법 제132조의2).

대상: 주택임차차입금·장기주택저당차입금(특별소득공제 중 주택자금), 주택청약종합저축,
신용카드 등 사용액, 벤처투자조합 등 간접투자, 국민성장펀드(2026년~, 규칙 값에 따름).
벤처기업 직접투자는 제외된다.
"""

from app.tax.result import BreakdownItem
from app.tax.rules.base import TaxRules


def aggregate_limit_adjustment(
    targets: list[BreakdownItem], venture_fund_amount: int, rules: TaxRules
) -> BreakdownItem:
    """종합한도 초과액을 음수 공제액으로 표현한 조정 항목을 반환한다."""
    subject_total = sum(x.amount for x in targets) + venture_fund_amount
    limit = rules.aggregate_deduction_limit
    excess = max(subject_total - limit, 0)
    return BreakdownItem(
        key="aggregate_limit",
        label="소득공제 종합한도 초과액",
        applied_amount=subject_total,
        amount=-excess,
        limited=excess > 0,
        description=(
            f"종합한도 대상 공제 합계 {subject_total:,}원 중 한도 {limit:,}원 초과분 차감"
            if excess
            else f"종합한도 대상 공제 합계 {subject_total:,}원 (한도 {limit:,}원 이내)"
        ),
    )
