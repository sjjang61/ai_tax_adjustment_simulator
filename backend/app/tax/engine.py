"""근로소득 연말정산 계산 파이프라인 (순수 함수).

총급여 − 근로소득공제 = 근로소득금액
근로소득금액 − 소득공제 = 과세표준 → × 기본세율 = 산출세액
산출세액 − 세액감면 − 세액공제 = 결정세액(0원 하한) → − 기납부세액 = 차감징수세액
지방소득세 = 결정세액 × 10%

특별공제(특별소득공제·특별세액공제·월세세액공제) 적용 방식과 표준세액공제 방식을 모두 계산해
결정세액이 적은 쪽을 자동으로 선택한다.
"""

from dataclasses import dataclass

from app.tax.credits.child import child_credit
from app.tax.credits.donation import donation_credits
from app.tax.credits.earned_income import earned_income_credit
from app.tax.credits.education import education_credit
from app.tax.credits.insurance import insurance_credit
from app.tax.credits.medical import medical_credit
from app.tax.credits.misc import marriage_credit, monthly_rent_credit, standard_credit
from app.tax.credits.pension_account import pension_account_credit
from app.tax.deductions.aggregate_limit import aggregate_limit_adjustment
from app.tax.deductions.card import card_deduction
from app.tax.deductions.earned_income import earned_income_deduction
from app.tax.deductions.housing import housing_deductions
from app.tax.deductions.insurance import pension_insurance_deduction, social_insurance_deduction
from app.tax.deductions.national_growth_fund import national_growth_fund_deduction
from app.tax.deductions.personal import personal_deduction
from app.tax.deductions.venture import venture_deduction
from app.tax.eligibility import Eligibility, evaluate
from app.tax.inputs import SimulationInput
from app.tax.money import apply_rate, format_percent, truncate_to_10_won
from app.tax.result import (
    BreakdownItem,
    CalcWarning,
    CreditMethod,
    LocalIncomeTax,
    MethodComparison,
    TaxResult,
    WarningLevel,
)
from app.tax.rules.base import TaxRules
from app.tax.tax_rate import CalculatedTax, calculate_tax

DISCLAIMER = (
    "이 결과는 참고용 시뮬레이션이며 실제 연말정산 결과와 다를 수 있습니다. "
    "정확한 금액은 국세청 홈택스 연말정산 간소화 서비스 및 회사 정산 결과를 확인하세요."
)


class RulesYearMismatchError(ValueError):
    pass


@dataclass(frozen=True)
class _Scenario:
    method: CreditMethod
    income_deductions: tuple[BreakdownItem, ...]
    total_income_deduction: int
    tax_base: int
    calculated: CalculatedTax
    tax_credits: tuple[BreakdownItem, ...]
    total_tax_credit: int
    determined_tax: int


def _group(key: str, label: str, children: tuple[BreakdownItem, ...]) -> BreakdownItem:
    return BreakdownItem(
        key=key,
        label=label,
        applied_amount=sum(x.applied_amount for x in children),
        amount=sum(x.amount for x in children),
        limited=any(x.limited for x in children),
        children=children,
    )


def _excluded(item: BreakdownItem) -> BreakdownItem:
    """표준세액공제 방식에서 제외되는 항목을 0원으로 표시한다."""
    return item.model_copy(
        update={
            "amount": 0,
            "limited": item.applied_amount > 0,
            "description": "표준세액공제 선택 시 미적용" if item.applied_amount else "",
            "children": (),
        }
    )


def _cap_credits(
    items: list[BreakdownItem], calculated_tax: int
) -> tuple[tuple[BreakdownItem, ...], int]:
    """세액공제 합계가 산출세액을 넘지 않도록 순서대로 적용한다 (소득세법 제61조 취지)."""
    remaining = calculated_tax
    capped: list[BreakdownItem] = []
    for item in items:
        applied = min(item.amount, remaining)
        remaining -= applied
        if applied < item.amount:
            lost = item.amount - applied
            item = item.model_copy(
                update={
                    "amount": applied,
                    "limited": True,
                    "description": (
                        f"{item.description} (산출세액 한도로 {lost:,}원 미적용)".strip()
                    ),
                }
            )
        capped.append(item)
    return tuple(capped), calculated_tax - remaining


def _run_scenario(
    method: CreditMethod,
    inp: SimulationInput,
    rules: TaxRules,
    eligibility: Eligibility,
    gross: int,
    earned_income_amount: int,
) -> _Scenario:
    itemized = method is CreditMethod.ITEMIZED
    d = inp.deductions
    c = inp.credits

    # ---- 소득공제 ----
    personal = personal_deduction(eligibility, rules)
    pension = pension_insurance_deduction(d)
    housing = housing_deductions(d, eligibility, rules, include_special=itemized)
    social = social_insurance_deduction(d)
    if not itemized:
        social = _excluded(social)
    special = _group("special", "특별소득공제", (social, housing.rent_loan, housing.mortgage))
    card = card_deduction(d.card, gross, eligibility.eligible_child_count, rules)
    venture = venture_deduction(d.venture_direct, d.venture_fund, earned_income_amount, rules)
    growth_fund = national_growth_fund_deduction(d.national_growth_fund, rules)
    other = _group(
        "other", "그 밖의 소득공제", (housing.subscription, card, venture.item, growth_fund)
    )
    aggregate_targets = [housing.rent_loan, housing.mortgage, housing.subscription, card]
    if rules.national_growth_fund and rules.national_growth_fund.included_in_aggregate_limit:
        aggregate_targets.append(growth_fund)
    aggregate = aggregate_limit_adjustment(aggregate_targets, venture.fund_amount, rules)
    income_deductions = (personal, pension, special, other, aggregate)
    total_income_deduction = sum(x.amount for x in income_deductions)
    tax_base = max(earned_income_amount - total_income_deduction, 0)

    # ---- 산출세액 ----
    calculated = calculate_tax(tax_base, rules)

    # ---- 세액공제 ----
    donations = donation_credits(c.donations, earned_income_amount, rules)
    special_credit = _group(
        "special_credit",
        "특별세액공제",
        (
            insurance_credit(c.insurance_general, c.insurance_disabled, rules),
            medical_credit(c.medical, gross, rules),
            education_credit(c.education, rules),
            donations.special,
        ),
    )
    rent = monthly_rent_credit(c.monthly_rent, gross, eligibility.monthly_rent_eligible, rules)
    credits: list[BreakdownItem] = [
        earned_income_credit(calculated.amount, gross, rules),
        child_credit(eligibility, rules),
        pension_account_credit(c.pension_savings, c.irp, gross, rules),
        special_credit if itemized else _excluded(special_credit),
        donations.statutory,
        rent if itemized else _excluded(rent),
        marriage_credit(inp.taxpayer.marriage_registered_this_year, rules),
    ]
    if not itemized:
        credits.append(standard_credit(rules))
    tax_credits, total_tax_credit = _cap_credits(credits, calculated.amount)

    # 결정세액: 음수 불가, 0원 하한 (세액감면은 미지원 → 0원)
    determined_tax = max(calculated.amount - total_tax_credit, 0)
    return _Scenario(
        method=method,
        income_deductions=income_deductions,
        total_income_deduction=total_income_deduction,
        tax_base=tax_base,
        calculated=calculated,
        tax_credits=tax_credits,
        total_tax_credit=total_tax_credit,
        determined_tax=determined_tax,
    )


def calculate(inp: SimulationInput, rules: TaxRules) -> TaxResult:
    if inp.tax_year != rules.tax_year:
        raise RulesYearMismatchError(
            f"입력 귀속연도({inp.tax_year})와 규칙 연도({rules.tax_year})가 다릅니다."
        )
    eligibility = evaluate(inp, rules)
    warnings: list[CalcWarning] = list(eligibility.warnings)

    gross = inp.gross_salary
    eid = earned_income_deduction(gross, rules)
    earned_income_amount = gross - eid.amount

    scenarios = [
        _run_scenario(method, inp, rules, eligibility, gross, earned_income_amount)
        for method in (CreditMethod.ITEMIZED, CreditMethod.STANDARD)
    ]
    # 결정세액이 같으면 특별공제 방식(내역이 더 자세함)을 우선한다.
    chosen = min(scenarios, key=lambda s: (s.determined_tax, s.method is CreditMethod.STANDARD))
    other = next(s for s in scenarios if s is not chosen)
    if chosen.method is CreditMethod.STANDARD and other.determined_tax > chosen.determined_tax:
        warnings.append(
            CalcWarning(
                code="standard_credit_selected",
                message=(
                    "표준세액공제가 더 유리해 자동 선택했습니다 (특별공제 적용 시 결정세액 "
                    f"{other.determined_tax:,}원)."
                ),
                level=WarningLevel.INFO,
            )
        )

    prepaid = inp.prepaid_tax.withholding + inp.prepaid_tax.previous_employer
    # 차감징수세액: 10원 미만 절사 (국고금 관리법 제47조)
    balance_due = truncate_to_10_won(chosen.determined_tax - prepaid)

    # 지방소득세: 결정세액 × 10% (원 미만 절사), 기납부분은 소득세 기납부세액의 10%로 추정
    local_rate = rules.local_income_tax_rate
    local_determined = apply_rate(chosen.determined_tax, local_rate)
    local_prepaid = apply_rate(prepaid, local_rate)
    local = LocalIncomeTax(
        determined_tax=local_determined,
        prepaid_tax=local_prepaid,
        balance_due=truncate_to_10_won(local_determined - local_prepaid),
    )

    return TaxResult(
        tax_year=inp.tax_year,
        rules_verified=rules.verified,
        annual_earned_income=inp.income.annual_earned_income,
        non_taxable_income=inp.income.non_taxable_income,
        gross_salary=gross,
        earned_income_deduction=eid,
        earned_income_amount=earned_income_amount,
        applied_method=chosen.method,
        method_comparison=tuple(
            MethodComparison(
                method=s.method,
                tax_base=s.tax_base,
                calculated_tax=s.calculated.amount,
                total_tax_credit=s.total_tax_credit,
                determined_tax=s.determined_tax,
            )
            for s in scenarios
        ),
        income_deductions=chosen.income_deductions,
        total_income_deduction=chosen.total_income_deduction,
        tax_base=chosen.tax_base,
        tax_rate=format_percent(chosen.calculated.bracket.rate),
        calculated_tax=chosen.calculated.amount,
        tax_reduction=0,
        tax_credits=chosen.tax_credits,
        total_tax_credit=chosen.total_tax_credit,
        determined_tax=chosen.determined_tax,
        prepaid_tax=prepaid,
        balance_due=balance_due,
        local_income_tax=local,
        total_balance_due=balance_due + local.balance_due,
        warnings=tuple(warnings),
        disclaimer=DISCLAIMER,
    )
