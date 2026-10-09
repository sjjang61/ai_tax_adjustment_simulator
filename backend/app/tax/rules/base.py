"""귀속연도별 세법 규칙 객체의 스키마.

계산 로직은 이 규칙 객체를 주입받아 사용하며, 세율·공제율·한도·구간 경계값은 모두 여기에 정의된
귀속연도 파일(``y{연도}.py``)의 인스턴스에서만 온다.
"""

from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ProgressiveBracket(_Frozen):
    """``lower`` 초과 ``upper`` 이하 구간: ``base_amount + (금액 - lower) × rate``."""

    lower: int
    upper: int | None
    base_amount: int
    rate: Decimal


class TaxRateBracket(_Frozen):
    """기본세율 구간 (누진공제액 방식): 세액 = 과세표준 × rate − progressive_deduction."""

    upper: int | None
    rate: Decimal
    progressive_deduction: int


class RateTier(_Frozen):
    """누적 금액 ``upper``까지 적용되는 공제율 구간 (upper=None이면 상한 없음)."""

    upper: int | None
    rate: Decimal


class LimitTier(_Frozen):
    """총급여 구간별 한도: ``max(base − (총급여 − lower) × reduction_rate, floor)``."""

    lower: int
    upper: int | None
    base: int
    reduction_rate: Decimal
    floor: int


class MortgageType(StrEnum):
    """장기주택저당차입금 이자상환액 공제 한도 유형 (소득세법 제52조 제5항)."""

    FIXED_AND_NON_DEFERRED_15Y = "fixed_and_non_deferred_15y"
    FIXED_OR_NON_DEFERRED_15Y = "fixed_or_non_deferred_15y"
    OTHER_15Y = "other_15y"
    FIXED_OR_NON_DEFERRED_10Y = "fixed_or_non_deferred_10y"


class EarnedIncomeDeductionRules(_Frozen):
    brackets: tuple[ProgressiveBracket, ...]
    max_deduction: int


class PersonalDeductionRules(_Frozen):
    basic_per_person: int
    elderly_additional: int
    elderly_min_age: int
    disabled_additional: int
    female_additional: int
    female_earned_income_limit: int
    single_parent_additional: int
    dependent_income_limit: int
    dependent_salary_only_limit: int
    ascendant_min_age: int
    descendant_max_age: int
    sibling_max_age: int
    sibling_min_age: int


class HousingRules(_Frozen):
    subscription_rate: Decimal
    subscription_payment_limit: int
    subscription_gross_salary_limit: int
    rent_loan_rate: Decimal
    rent_loan_and_subscription_limit: int
    mortgage_limits: dict[MortgageType, int]


class CardRules(_Frozen):
    minimum_usage_rate: Decimal
    credit_rate: Decimal
    debit_cash_rate: Decimal
    culture_rate: Decimal
    sports_facility_rate: Decimal
    traditional_market_rate: Decimal
    public_transport_rate: Decimal
    culture_gross_salary_limit: int
    limit_salary_threshold: int
    basic_limit_low_income: int
    basic_limit_high_income: int
    additional_limit_low_income: int
    additional_limit_high_income: int
    child_basic_limit_per_child_low_income: int
    child_basic_limit_per_child_high_income: int
    child_basic_limit_max_low_income: int
    child_basic_limit_max_high_income: int


class VentureRules(_Frozen):
    direct_tiers: tuple[RateTier, ...]
    fund_rate: Decimal
    income_limit_rate: Decimal


class NationalGrowthFundRules(_Frozen):
    """국민참여형 국민성장펀드 투자 소득공제 (2026년 귀속 신설)."""

    tiers: tuple[RateTier, ...]
    max_deduction: int
    min_holding_years: int
    included_in_aggregate_limit: bool


class EarnedIncomeCreditRules(_Frozen):
    tax_threshold: int
    low_rate: Decimal
    high_rate: Decimal
    limit_tiers: tuple[LimitTier, ...]


class ChildCreditRules(_Frozen):
    min_age: int
    first_child: int
    second_child: int
    third_plus_child: int
    birth_first: int
    birth_second: int
    birth_third_plus: int


class PensionAccountRules(_Frozen):
    savings_limit: int
    combined_limit: int
    high_rate_gross_salary_limit: int
    high_rate: Decimal
    low_rate: Decimal


class InsuranceCreditRules(_Frozen):
    general_limit: int
    general_rate: Decimal
    disabled_limit: int
    disabled_rate: Decimal


class MedicalCreditRules(_Frozen):
    threshold_rate: Decimal
    general_limit: int
    general_rate: Decimal
    specific_rate: Decimal
    premature_rate: Decimal
    infertility_rate: Decimal
    specific_min_age: int  # 이 나이 이상 부양가족 의료비는 한도 없는 특정 의료비
    specific_max_age_at_start: int  # 과세기간 개시일 현재 이 나이 이하도 특정 의료비


class EducationCreditRules(_Frozen):
    rate: Decimal
    preschool_limit: int
    school_limit: int
    university_limit: int


class DonationCreditRules(_Frozen):
    political_full_credit_limit: int
    political_full_credit_ratio: Decimal
    political_tiers: tuple[RateTier, ...]
    hometown_full_credit_limit: int
    hometown_full_credit_ratio: Decimal
    hometown_rate: Decimal
    hometown_disaster_rate: Decimal
    hometown_annual_limit: int
    general_tiers: tuple[RateTier, ...]
    general_limit_rate: Decimal
    religious_limit_rate: Decimal
    religious_extra_limit_rate: Decimal


class RentCreditRules(_Frozen):
    gross_salary_limit: int
    high_rate_gross_salary_limit: int
    high_rate: Decimal
    low_rate: Decimal
    payment_limit: int


class TaxRules(_Frozen):
    """한 귀속연도의 근로소득 연말정산 규칙 묶음."""

    tax_year: int
    verified: bool
    notes: tuple[str, ...]
    earned_income_deduction: EarnedIncomeDeductionRules
    personal: PersonalDeductionRules
    housing: HousingRules
    card: CardRules
    venture: VentureRules
    national_growth_fund: NationalGrowthFundRules | None  # None = 해당 연도 미시행
    aggregate_deduction_limit: int
    tax_rate_brackets: tuple[TaxRateBracket, ...]
    earned_income_credit: EarnedIncomeCreditRules
    child_credit: ChildCreditRules
    pension_account: PensionAccountRules
    insurance_credit: InsuranceCreditRules
    medical_credit: MedicalCreditRules
    education_credit: EducationCreditRules
    donation_credit: DonationCreditRules
    rent_credit: RentCreditRules
    standard_credit: int
    marriage_credit: int | None
    local_income_tax_rate: Decimal
