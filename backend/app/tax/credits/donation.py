"""기부금 세액공제.

- 정치자금기부금 (조특법 제76조), 고향사랑기부금 (조특법 제58조): 표준세액공제와 함께 적용 가능
- 특례·일반기부금 (소득세법 제59조의4 제4항, 제34조): 특별세액공제 — 표준세액공제 선택 시 미적용

한도 차감 순서: 정치자금 → 고향사랑 → 특례 → 일반(종교단체 외 → 종교단체).
"""

from dataclasses import dataclass
from decimal import Decimal

from app.tax.inputs import Donations
from app.tax.money import apply_rate, format_percent, truncate_won
from app.tax.result import BreakdownItem
from app.tax.rules.base import TaxRules
from app.tax.tiers import describe_tiers, tiered_amount


@dataclass(frozen=True)
class DonationCredits:
    statutory: BreakdownItem  # 정치자금·고향사랑 (조특법)
    special: BreakdownItem  # 특례·일반 (특별세액공제)


def donation_credits(d: Donations, earned_income_amount: int, rules: TaxRules) -> DonationCredits:
    r = rules.donation_credit
    income = earned_income_amount

    # 정치자금: 한도 = 소득금액. 10만원 이하 100/110, 초과분 구간별 공제율
    political = min(d.political, income)
    political_full = min(political, r.political_full_credit_limit)
    political_credit = truncate_won(
        Decimal(political_full) * r.political_full_credit_ratio
    ) + tiered_amount(political, r.political_tiers, start=r.political_full_credit_limit)
    political_item = BreakdownItem(
        key="donation.political",
        label="정치자금기부금",
        applied_amount=d.political,
        amount=political_credit,
        limited=political < d.political,
        description=(
            f"{r.political_full_credit_limit:,}원 이하 100/110, 초과분 "
            f"{describe_tiers(r.political_tiers)}"
        ),
    )

    # 고향사랑: 연간 한도 및 남은 소득금액 한도. 10만원 이하분은 일반 기부분부터 100/110 적용
    hometown_total = d.hometown + d.hometown_disaster
    hometown_eligible = min(hometown_total, r.hometown_annual_limit, max(income - political, 0))
    regular = min(d.hometown, hometown_eligible)
    disaster = hometown_eligible - regular
    full_regular = min(regular, r.hometown_full_credit_limit)
    full_disaster = min(disaster, r.hometown_full_credit_limit - full_regular)
    hometown_credit = truncate_won(
        Decimal(full_regular + full_disaster) * r.hometown_full_credit_ratio
        + Decimal(regular - full_regular) * r.hometown_rate
        + Decimal(disaster - full_disaster) * r.hometown_disaster_rate
    )
    hometown_item = BreakdownItem(
        key="donation.hometown",
        label="고향사랑기부금",
        applied_amount=hometown_total,
        amount=hometown_credit,
        limited=hometown_eligible < hometown_total,
        description=(
            f"{r.hometown_full_credit_limit:,}원 이하 100/110, 초과분 "
            f"{format_percent(r.hometown_rate)} (특별재난지역 {format_percent(r.hometown_disaster_rate)}), "
            f"연간 한도 {r.hometown_annual_limit:,}원"
        ),
    )

    # 특례기부금: 한도 = 소득금액 − 정치자금 − 고향사랑
    base = max(income - political - hometown_eligible, 0)
    special = min(d.special, base)

    # 일반기부금: 한도 = (소득금액 − 위 기부금) × 30%,
    # 종교단체 기부금이 있으면 × 10% + min(× 20%, 종교단체 외 기부금)
    general_base = base - special
    if d.religious:
        general_limit = apply_rate(general_base, r.religious_limit_rate) + min(
            apply_rate(general_base, r.religious_extra_limit_rate), d.general
        )
    else:
        general_limit = apply_rate(general_base, r.general_limit_rate)
    general_eligible = min(d.general + d.religious, general_limit)

    eligible = special + general_eligible
    special_credit = tiered_amount(eligible, r.general_tiers)
    requested = d.special + d.general + d.religious
    special_item = BreakdownItem(
        key="donation.special_general",
        label="특례·일반기부금",
        applied_amount=requested,
        amount=special_credit,
        limited=eligible < requested,
        description=(
            f"공제대상 {eligible:,}원 (특례 {special:,}원 + 일반 {general_eligible:,}원, "
            f"일반기부금 한도 {general_limit:,}원) × {describe_tiers(r.general_tiers)}"
            if requested
            else ""
        ),
    )

    statutory_children = tuple(x for x in (political_item, hometown_item) if x.applied_amount)
    statutory = BreakdownItem(
        key="donation.statutory",
        label="정치자금·고향사랑기부금",
        applied_amount=d.political + hometown_total,
        amount=political_credit + hometown_credit,
        limited=any(x.limited for x in statutory_children),
        children=statutory_children,
    )
    return DonationCredits(statutory=statutory, special=special_item)
