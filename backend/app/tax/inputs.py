"""계산 엔진 입력 모델.

모든 금액은 원 단위 정수다. 알 수 없는 필드는 거부한다(extra="forbid").
형식·범위 검증만 수행하며, 공제 요건 판정은 ``eligibility`` 모듈이 경고로 처리한다.
"""

from enum import StrEnum
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.tax.rules.base import MortgageType

MAX_WON = 10_000_000_000_000  # 10조원: 입력 상한 (오입력 방지용 형식 검증)

Won = Annotated[int, Field(ge=0, le=MAX_WON)]
BirthYear = Annotated[int, Field(ge=1900, le=2100)]


class _Input(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Relation(StrEnum):
    SPOUSE = "spouse"  # 배우자
    LINEAL_ASCENDANT = "lineal_ascendant"  # 직계존속 (부모·조부모 등)
    LINEAL_DESCENDANT = "lineal_descendant"  # 직계비속·입양자 (자녀·손자녀)
    SIBLING = "sibling"  # 형제자매
    FOSTER_CHILD = "foster_child"  # 위탁아동


class Dependent(_Input):
    """부양가족 (본인 제외)."""

    name: str = Field(default="", max_length=50)
    relation: Relation
    birth_year: BirthYear
    disabled: bool = False
    income_amount: Won = Field(
        default=0, description="연간 소득금액 합계 (근로소득만 있으면 총급여)"
    )
    income_is_salary_only: bool = Field(default=False, description="근로소득만 있는지 여부")
    born_or_adopted_this_year: bool = Field(default=False, description="해당 연도 출생·입양 여부")
    child_order: int | None = Field(default=None, ge=1, le=20, description="출생·입양 자녀의 순서")


class Taxpayer(_Input):
    birth_year: BirthYear
    is_female: bool = False
    is_married: bool = Field(default=False, description="배우자가 있는지 여부")
    is_household_head: bool = False
    disabled: bool = False
    is_homeless: bool = Field(
        default=False, description="무주택 세대주(또는 요건 충족 세대원) 여부"
    )
    marriage_registered_this_year: bool = Field(
        default=False, description="해당 연도 혼인신고 여부"
    )


class Income(_Input):
    annual_earned_income: Won = Field(description="연간 근로소득 (비과세 포함)")
    non_taxable_income: Won = 0

    @model_validator(mode="after")
    def _non_taxable_within_income(self) -> Self:
        if self.non_taxable_income > self.annual_earned_income:
            raise ValueError("비과세소득은 연간 근로소득을 초과할 수 없습니다.")
        return self


class PrepaidTax(_Input):
    withholding: Won = Field(default=0, description="현 근무지 원천징수 소득세")
    previous_employer: Won = Field(default=0, description="종전 근무지 결정세액")


class CardUsage(_Input):
    credit: Won = 0  # 신용카드
    debit_cash: Won = 0  # 직불·선불카드, 현금영수증
    culture: Won = 0  # 도서·신문·공연·박물관·미술관·영화관람료
    sports_facility: Won = 0  # 수영장·체력단련장 시설이용료 (2025.7.1. 이후)
    traditional_market: Won = 0  # 전통시장
    public_transport: Won = 0  # 대중교통

    @property
    def total(self) -> int:
        return (
            self.credit
            + self.debit_cash
            + self.culture
            + self.sports_facility
            + self.traditional_market
            + self.public_transport
        )


class IncomeDeductionInput(_Input):
    national_pension: Won = 0  # 국민연금 등 연금보험료
    health_insurance: Won = 0  # 건강보험료(장기요양 포함)
    employment_insurance: Won = 0  # 고용보험료
    housing_rent_loan_repayment: Won = 0  # 주택임차차입금 원리금상환액
    long_term_mortgage_interest: Won = 0  # 장기주택저당차입금 이자상환액
    mortgage_type: MortgageType | None = None
    housing_subscription: Won = 0  # 주택청약종합저축 납입액
    card: CardUsage = CardUsage()
    venture_direct: Won = 0  # 벤처기업 등 직접 투자
    venture_fund: Won = 0  # 벤처투자조합 등 간접 투자
    national_growth_fund: Won = 0  # 국민성장펀드 전용계좌 납입액 (2026년 귀속부터)


class MedicalExpenses(_Input):
    general: Won = 0  # 그 밖의 부양가족 의료비 (연 700만원 한도)
    specific: Won = 0  # 본인·65세 이상·장애인·6세 이하·건강보험산정특례자
    premature: Won = 0  # 미숙아·선천성이상아
    infertility: Won = 0  # 난임시술비


class EducationKind(StrEnum):
    SELF = "self"  # 본인 (한도 없음)
    PRESCHOOL = "preschool"  # 취학전 아동
    SCHOOL = "school"  # 초·중·고
    UNIVERSITY = "university"  # 대학생
    DISABLED_SPECIAL = "disabled_special"  # 장애인 특수교육비 (한도 없음)


class EducationExpense(_Input):
    """교육비 1건 = 교육 대상자 1명의 연간 교육비."""

    kind: EducationKind
    amount: Won
    label: str = Field(default="", max_length=50)


class Donations(_Input):
    political: Won = 0  # 정치자금기부금
    hometown: Won = 0  # 고향사랑기부금
    hometown_disaster: Won = 0  # 특별재난지역 고향사랑기부금
    special: Won = 0  # 특례기부금
    general: Won = 0  # 일반기부금 (종교단체 외)
    religious: Won = 0  # 일반기부금 (종교단체)


class TaxCreditInput(_Input):
    pension_savings: Won = 0  # 연금저축
    irp: Won = 0  # 퇴직연금(IRP 등)
    insurance_general: Won = 0  # 보장성보험료
    insurance_disabled: Won = 0  # 장애인전용 보장성보험료
    medical: MedicalExpenses = MedicalExpenses()
    education: tuple[EducationExpense, ...] = Field(default=(), max_length=30)
    donations: Donations = Donations()
    monthly_rent: Won = 0  # 월세 지급액


class SimulationInput(_Input):
    tax_year: int = Field(ge=2000, le=2100)
    income: Income
    prepaid_tax: PrepaidTax = PrepaidTax()
    taxpayer: Taxpayer
    dependents: tuple[Dependent, ...] = Field(default=(), max_length=30)
    deductions: IncomeDeductionInput = IncomeDeductionInput()
    credits: TaxCreditInput = TaxCreditInput()

    @property
    def gross_salary(self) -> int:
        """총급여 = 연간 근로소득 − 비과세소득."""
        return self.income.annual_earned_income - self.income.non_taxable_income
