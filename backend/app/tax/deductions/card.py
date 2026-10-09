"""신용카드 등 사용금액 소득공제 (조특법 제126조의2).

1. 최저사용금액(총급여 × 25%)을 신용카드 → 직불·현금 → 도서·공연 → 체육시설 → 전통시장 → 대중교통
   순서로 차감한다 (국세청 신용카드 등 소득공제 명세서 계산 순서).
2. 남은 사용액에 결제수단별 공제율을 곱해 공제가능금액을 구한다.
3. 기본한도까지 공제하고, 초과분은 추가공제(전통시장·대중교통·도서등)의 공제가능금액 범위에서
   추가한도까지 더 공제한다.
"""

from decimal import Decimal

from app.tax.inputs import CardUsage
from app.tax.money import apply_rate, format_percent
from app.tax.result import BreakdownItem
from app.tax.rules.base import TaxRules


def card_deduction(
    card: CardUsage, gross_salary: int, eligible_child_count: int, rules: TaxRules
) -> BreakdownItem:
    r = rules.card
    culture_ok = gross_salary <= r.culture_gross_salary_limit
    credit_amount = card.credit
    culture_amount = card.culture
    sports_amount = card.sports_facility
    if not culture_ok:
        # 총급여 7천만원 초과자의 도서·공연·체육시설 사용분은 신용카드 공제율로 계산 (보수적 가정)
        credit_amount += culture_amount + sports_amount
        culture_amount = sports_amount = 0

    categories: list[tuple[str, str, int, Decimal, bool]] = [
        ("credit", "신용카드", credit_amount, r.credit_rate, False),
        ("debit_cash", "직불·선불카드·현금영수증", card.debit_cash, r.debit_cash_rate, False),
        ("culture", "도서·공연·박물관·미술관·영화", culture_amount, r.culture_rate, culture_ok),
        ("sports_facility", "수영장·체력단련장", sports_amount, r.sports_facility_rate, culture_ok),
        (
            "traditional_market",
            "전통시장",
            card.traditional_market,
            r.traditional_market_rate,
            True,
        ),
        ("public_transport", "대중교통", card.public_transport, r.public_transport_rate, True),
    ]

    # 최저사용금액: 총급여 × 25%, 원 미만 절사
    minimum_usage = apply_rate(gross_salary, r.minimum_usage_rate)
    remaining_min = minimum_usage
    children: list[BreakdownItem] = []
    deductible_total = 0
    additional_pool = 0
    for key, label, amount, rate, counts_for_additional in categories:
        excluded = min(amount, remaining_min)
        remaining_min -= excluded
        deductible = apply_rate(amount - excluded, rate)
        deductible_total += deductible
        if counts_for_additional:
            additional_pool += deductible
        if amount:
            children.append(
                BreakdownItem(
                    key=f"other.card.{key}",
                    label=label,
                    applied_amount=amount,
                    amount=deductible,
                    description=(
                        f"(사용액 − 최저사용금액 차감 {excluded:,}원) × {format_percent(rate)}"
                    ),
                )
            )

    low_income = gross_salary <= r.limit_salary_threshold
    if low_income:
        child_extra = min(
            eligible_child_count * r.child_basic_limit_per_child_low_income,
            r.child_basic_limit_max_low_income,
        )
        basic_limit = r.basic_limit_low_income + child_extra
        additional_limit = r.additional_limit_low_income
    else:
        child_extra = min(
            eligible_child_count * r.child_basic_limit_per_child_high_income,
            r.child_basic_limit_max_high_income,
        )
        basic_limit = r.basic_limit_high_income + child_extra
        additional_limit = r.additional_limit_high_income

    basic = min(deductible_total, basic_limit)
    additional = min(deductible_total - basic, additional_pool, additional_limit)
    amount = basic + additional

    total_usage = card.total
    if total_usage == 0:
        description = ""
    elif total_usage <= minimum_usage:
        description = f"사용액이 최저사용금액(총급여의 25%, {minimum_usage:,}원) 이하로 공제 없음"
    else:
        description = (
            f"최저사용금액 {minimum_usage:,}원 초과분 공제가능액 {deductible_total:,}원 중 "
            f"기본한도 {basic_limit:,}원"
            + (f"(자녀 추가 {child_extra:,}원 포함)" if child_extra else "")
            + f" + 추가공제 {additional:,}원(추가한도 {additional_limit:,}원)"
        )
    return BreakdownItem(
        key="other.card",
        label="신용카드 등 사용액",
        applied_amount=total_usage,
        amount=amount,
        limited=amount < deductible_total,
        description=description,
        children=tuple(children),
    )
