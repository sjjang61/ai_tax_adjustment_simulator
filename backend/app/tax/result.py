"""계산 엔진 출력 모델 (불변)."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class _Output(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class AppliedUnit(StrEnum):
    WON = "won"  # 원
    COUNT = "count"  # 명·건


class BreakdownItem(_Output):
    """공제·세액공제 항목 하나의 계산 내역.

    - applied_amount: 공제 적용 대상 금액(입력 사용액·납입액 등) 또는 인원·건수 (applied_unit)
    - amount: 최종 공제액 (소득공제액 또는 세액공제액, 원)
    - limited: 한도·요건으로 공제액이 줄었는지 여부
    """

    key: str
    label: str
    applied_amount: int
    applied_unit: AppliedUnit = AppliedUnit.WON
    amount: int
    limited: bool = False
    description: str = ""
    children: tuple["BreakdownItem", ...] = ()


class WarningLevel(StrEnum):
    INFO = "info"
    WARNING = "warning"


class CalcWarning(_Output):
    code: str
    message: str
    level: WarningLevel = WarningLevel.WARNING
    field: str | None = None


class CreditMethod(StrEnum):
    ITEMIZED = "itemized"  # 특별소득공제·특별세액공제·월세세액공제 적용
    STANDARD = "standard"  # 표준세액공제 적용


class MethodComparison(_Output):
    method: CreditMethod
    tax_base: int
    calculated_tax: int
    total_tax_credit: int
    determined_tax: int


class LocalIncomeTax(_Output):
    determined_tax: int
    prepaid_tax: int
    balance_due: int


class TaxResult(_Output):
    tax_year: int
    rules_verified: bool

    annual_earned_income: int
    non_taxable_income: int
    gross_salary: int
    earned_income_deduction: BreakdownItem
    earned_income_amount: int

    applied_method: CreditMethod
    method_comparison: tuple[MethodComparison, ...]

    income_deductions: tuple[BreakdownItem, ...]
    total_income_deduction: int
    tax_base: int
    tax_rate: str
    calculated_tax: int
    tax_reduction: int
    tax_credits: tuple[BreakdownItem, ...]
    total_tax_credit: int
    determined_tax: int

    prepaid_tax: int
    balance_due: int
    local_income_tax: LocalIncomeTax
    total_balance_due: int

    warnings: tuple[CalcWarning, ...]
    disclaimer: str
