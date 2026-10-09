"""주택자금 소득공제.

- 주택임차차입금 원리금상환액 (소득세법 제52조 제4항) — 특별소득공제
- 장기주택저당차입금 이자상환액 (소득세법 제52조 제5항) — 특별소득공제
- 주택청약종합저축 (조특법 제87조 제2항) — 그 밖의 소득공제

한도 적용 순서: 주택임차차입금 → 장기주택저당차입금 → 주택청약종합저축.
주택임차차입금과 주택청약은 합산 400만원, 여기에 장기주택저당차입금을 합산해 유형별 한도를 적용한다.
"""

from dataclasses import dataclass

from app.tax.eligibility import Eligibility
from app.tax.inputs import IncomeDeductionInput
from app.tax.money import apply_rate, format_percent
from app.tax.result import BreakdownItem
from app.tax.rules.base import TaxRules


@dataclass(frozen=True)
class HousingDeductions:
    rent_loan: BreakdownItem
    mortgage: BreakdownItem
    subscription: BreakdownItem


def housing_deductions(
    d: IncomeDeductionInput,
    eligibility: Eligibility,
    rules: TaxRules,
    *,
    include_special: bool,
) -> HousingDeductions:
    """``include_special=False``(표준세액공제 선택)이면 특별소득공제인 주택자금 공제를 제외한다."""
    h = rules.housing

    # 1) 주택임차차입금 원리금상환액 × 40%, 주택청약과 합산 400만원
    rent_loan_raw = 0
    rent_loan_desc = ""
    if not include_special and d.housing_rent_loan_repayment:
        rent_loan_desc = "표준세액공제 선택 시 특별소득공제 미적용"
    elif not eligibility.rent_loan_eligible:
        rent_loan_desc = "무주택 세대주 요건 미충족"
    else:
        rent_loan_raw = apply_rate(d.housing_rent_loan_repayment, h.rent_loan_rate)
        rent_loan_desc = f"상환액 × {format_percent(h.rent_loan_rate)}"
    rent_loan_amount = min(rent_loan_raw, h.rent_loan_and_subscription_limit)
    if rent_loan_amount < rent_loan_raw:
        rent_loan_desc += f" → 한도 {h.rent_loan_and_subscription_limit:,}원"
    rent_loan = BreakdownItem(
        key="special.housing_rent_loan",
        label="주택임차차입금 원리금상환액",
        applied_amount=d.housing_rent_loan_repayment,
        amount=rent_loan_amount,
        limited=rent_loan_amount < rent_loan_raw
        or (d.housing_rent_loan_repayment > 0 and rent_loan_raw == 0),
        description=rent_loan_desc,
    )

    # 2) 장기주택저당차입금 이자상환액: 위 공제와 합산해 유형별 한도
    mortgage_limit: int | None = None
    mortgage_amount = 0
    mortgage_desc = ""
    if d.long_term_mortgage_interest:
        if not include_special:
            mortgage_desc = "표준세액공제 선택 시 특별소득공제 미적용"
        elif d.mortgage_type is None:
            mortgage_desc = "한도 유형 미선택"
        else:
            mortgage_limit = h.mortgage_limits[d.mortgage_type]
            room = max(mortgage_limit - rent_loan_amount, 0)
            mortgage_amount = min(d.long_term_mortgage_interest, room)
            mortgage_desc = f"이자상환액 전액, 주택임차차입금 공제와 합산 한도 {mortgage_limit:,}원"
    mortgage = BreakdownItem(
        key="special.long_term_mortgage",
        label="장기주택저당차입금 이자상환액",
        applied_amount=d.long_term_mortgage_interest,
        amount=mortgage_amount,
        limited=mortgage_amount < d.long_term_mortgage_interest,
        description=mortgage_desc,
    )

    # 3) 주택청약종합저축: 납입액(연 300만원 한도) × 40%
    subscription_amount = 0
    subscription_desc = ""
    subscription_limited = False
    if d.housing_subscription:
        if not eligibility.housing_subscription_eligible:
            subscription_desc = "무주택 세대주·총급여 요건 미충족"
            subscription_limited = True
        else:
            base = min(d.housing_subscription, h.subscription_payment_limit)
            raw = apply_rate(base, h.subscription_rate)
            room = h.rent_loan_and_subscription_limit - rent_loan_amount
            if mortgage_limit is not None:
                room = min(room, mortgage_limit - rent_loan_amount - mortgage_amount)
            subscription_amount = max(min(raw, room), 0)
            subscription_limited = base < d.housing_subscription or subscription_amount < raw
            subscription_desc = (
                f"min(납입액, {h.subscription_payment_limit:,}원) × "
                f"{format_percent(h.subscription_rate)}"
            )
            if subscription_amount < raw:
                subscription_desc += " → 주택임차차입금 등과 합산 한도 적용"
    subscription = BreakdownItem(
        key="other.housing_subscription",
        label="주택청약종합저축",
        applied_amount=d.housing_subscription,
        amount=subscription_amount,
        limited=subscription_limited,
        description=subscription_desc,
    )
    return HousingDeductions(rent_loan=rent_loan, mortgage=mortgage, subscription=subscription)
