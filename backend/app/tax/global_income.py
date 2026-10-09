"""종합소득세 계산 (순수 함수): 근로소득 + 사업소득 + 기타소득.

- 근로소득·인적공제·공제 입력은 연말정산 입력(``SimulationInput``)을 그대로 사용한다.
- 사업소득금액 = 총수입금액 − 필요경비 (장부 또는 경비율). 결손이면 다른 종합소득에서 차감(이월은 미지원).
- 기타소득금액 = 총수입금액 − 필요경비 (강연료·원고료 등은 60% 의제와 실제 중 큰 금액).
- 기타소득금액 합계가 300만원 이하면 분리과세(20%, 과세 종결)와 종합과세 중 선택할 수 있으며,
  기본값(auto)은 세부담이 적은 쪽을 고른다.
- 기납부세액 = 근로소득 연말정산 결정세액 + 사업소득 원천징수 + (종합과세 시) 기타소득 원천징수 + 중간예납.
- 세액 계산은 연말정산 계산 엔진(``calculate``)에 그 밖의 종합소득금액을 넘겨 수행한다.
"""

from decimal import Decimal
from enum import StrEnum
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.tax.engine import calculate
from app.tax.inputs import SimulationInput, Won
from app.tax.money import apply_rate, format_percent, truncate_won
from app.tax.result import CalcWarning, TaxResult, WarningLevel
from app.tax.rules.base import TaxRules

GLOBAL_DISCLAIMER = (
    "이 결과는 참고용 시뮬레이션이며 실제 종합소득세 신고 결과와 다를 수 있습니다. "
    "정확한 금액은 국세청 홈택스 종합소득세 신고 서비스에서 확인하세요."
)
MAX_INCOME_ITEMS = 20


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ExpenseMethod(StrEnum):
    BOOK = "book"  # 장부: 실제 필요경비
    RATE = "rate"  # 경비율: 국세청 업종별 단순경비율 등 (사용자가 입력)


class BusinessIncome(_Model):
    name: str = Field(default="", max_length=50)
    revenue: Won = Field(description="총수입금액")
    expense_method: ExpenseMethod = ExpenseMethod.RATE
    expenses: Won = Field(default=0, description="장부 방식의 필요경비")
    expense_rate: Decimal = Field(
        default=Decimal("0"), ge=0, le=100, description="경비율(%) — 국세청 업종별 경비율 조회"
    )
    withholding_tax: Won | None = Field(
        default=None, description="원천징수된 소득세. 비우면 총수입금액 × 3%로 추정"
    )


class OtherIncomeKind(StrEnum):
    DEEMED_EXPENSE = "deemed_expense"  # 강연료·원고료·인적용역 일시소득 등 (필요경비 60% 의제)
    ACTUAL = "actual"  # 실제 필요경비만 인정


class OtherIncome(_Model):
    name: str = Field(default="", max_length=50)
    kind: OtherIncomeKind = OtherIncomeKind.DEEMED_EXPENSE
    revenue: Won = Field(description="총수입금액 (지급액)")
    expenses: Won = Field(default=0, description="실제 필요경비")
    withholding_tax: Won | None = Field(
        default=None, description="원천징수된 소득세. 비우면 기타소득금액 × 20%로 추정"
    )


class OtherIncomeTaxation(StrEnum):
    AUTO = "auto"
    COMPREHENSIVE = "comprehensive"
    SEPARATE = "separate"


class GlobalIncomeInput(_Model):
    tax_year: int = Field(ge=2000, le=2100)
    base: SimulationInput = Field(
        description="근로소득·인적공제·공제 입력 (근로소득이 없으면 급여 0)"
    )
    earned_prepaid_tax: Won | None = Field(
        default=None,
        description="근로소득 기납부세액(연말정산 결정세액). 비우면 연말정산 결정세액으로 계산",
    )
    business_incomes: tuple[BusinessIncome, ...] = Field(default=(), max_length=MAX_INCOME_ITEMS)
    other_incomes: tuple[OtherIncome, ...] = Field(default=(), max_length=MAX_INCOME_ITEMS)
    other_income_taxation: OtherIncomeTaxation = OtherIncomeTaxation.AUTO
    interim_prepayment: Won = Field(default=0, description="중간예납세액")

    @model_validator(mode="after")
    def _same_year(self) -> Self:
        if self.base.tax_year != self.tax_year:
            raise ValueError("근로소득 입력의 귀속연도가 종합소득세 귀속연도와 같아야 합니다.")
        return self


IncomeKind = Literal["earned", "business", "other"]
Taxation = Literal["comprehensive", "separate"]


class IncomeLine(_Model):
    kind: IncomeKind
    name: str
    revenue: int  # 총수입금액 (근로소득은 총급여)
    expenses: int  # 필요경비 (근로소득은 근로소득공제)
    income_amount: int  # 소득금액 (사업소득은 결손 시 음수)
    withholding_tax: int
    note: str = ""


class PrepaidBreakdown(_Model):
    earned_settled: int  # 근로소득 연말정산 결정세액
    business_withholding: int
    other_withholding: int  # 종합과세 기타소득의 원천징수세액
    interim_prepayment: int
    total: int


class TaxationOption(_Model):
    taxation: Taxation
    comprehensive_income_amount: int
    determined_tax: int  # 종합소득 결정세액
    local_income_tax: int
    separate_tax: int  # 분리과세 기타소득 소득세 (과세 종결)
    separate_local_tax: int
    total_burden: int  # 소득세 + 지방소득세 합계 부담


class GlobalIncomeResult(_Model):
    tax_year: int
    rules_verified: bool
    income_lines: tuple[IncomeLine, ...]
    earned_income_amount: int
    business_income_amount: int
    other_income_amount: int  # 종합과세분 (분리과세면 0)
    comprehensive_income_amount: int
    other_income_taxation: Literal["comprehensive", "separate", "none"]
    separate_tax: int
    options: tuple[TaxationOption, ...]
    prepaid: PrepaidBreakdown
    tax_result: TaxResult
    total_balance_due: int  # 납부(+)/환급(−), 지방소득세 포함
    warnings: tuple[CalcWarning, ...]
    disclaimer: str


def business_line(b: BusinessIncome, rules: TaxRules) -> IncomeLine:
    g = rules.global_income
    if b.expense_method is ExpenseMethod.BOOK:
        expenses = b.expenses
        method = "장부"
    else:
        # 경비율 적용, 원 미만 절사
        expenses = truncate_won(Decimal(b.revenue) * b.expense_rate / 100)
        method = f"경비율 {b.expense_rate.normalize():f}%"
    notes = [method]
    if b.withholding_tax is None:
        withholding = apply_rate(b.revenue, g.business_withholding_rate)
        notes.append(f"원천징수 {format_percent(g.business_withholding_rate)} 추정")
    else:
        withholding = b.withholding_tax
    return IncomeLine(
        kind="business",
        name=b.name or "사업소득",
        revenue=b.revenue,
        expenses=expenses,
        income_amount=b.revenue - expenses,
        withholding_tax=withholding,
        note=", ".join(notes),
    )


def other_line(o: OtherIncome, rules: TaxRules) -> IncomeLine:
    g = rules.global_income
    if o.kind is OtherIncomeKind.DEEMED_EXPENSE:
        # 필요경비 의제(60%)와 실제 필요경비 중 큰 금액 (소득세법 시행령 제87조)
        expenses = max(apply_rate(o.revenue, g.other_deemed_expense_rate), o.expenses)
        notes = [f"필요경비 {format_percent(g.other_deemed_expense_rate)} 의제"]
    else:
        expenses = o.expenses
        notes = ["실제 필요경비"]
    amount = max(o.revenue - expenses, 0)
    if o.withholding_tax is None:
        withholding = apply_rate(amount, g.other_withholding_rate)
        notes.append(f"원천징수 {format_percent(g.other_withholding_rate)} 추정")
    else:
        withholding = o.withholding_tax
    return IncomeLine(
        kind="other",
        name=o.name or "기타소득",
        revenue=o.revenue,
        expenses=expenses,
        income_amount=amount,
        withholding_tax=withholding,
        note=", ".join(notes),
    )


def _with_prepaid(base: SimulationInput, prepaid: int) -> SimulationInput:
    return base.model_copy(
        update={
            "prepaid_tax": base.prepaid_tax.model_copy(
                update={"withholding": prepaid, "previous_employer": 0}
            )
        }
    )


def calculate_global(inp: GlobalIncomeInput, rules: TaxRules) -> GlobalIncomeResult:
    g = rules.global_income
    warnings: list[CalcWarning] = []
    base = inp.base

    business = [business_line(b, rules) for b in inp.business_incomes]
    others = [other_line(o, rules) for o in inp.other_incomes]
    business_total = sum(x.income_amount for x in business)
    other_total = sum(x.income_amount for x in others)
    business_wh = sum(x.withholding_tax for x in business)
    other_wh = sum(x.withholding_tax for x in others)

    # 근로소득 기납부세액: 연말정산 결정세액 (입력 시 그 값)
    earned_settled = (
        inp.earned_prepaid_tax
        if inp.earned_prepaid_tax is not None
        else (calculate(base, rules).determined_tax if base.gross_salary > 0 else 0)
    )

    if business_total < 0:
        warnings.append(
            CalcWarning(
                code="business_loss",
                message=(
                    f"사업소득 결손금 {-business_total:,}원을 다른 종합소득금액에서 차감했습니다. "
                    "남는 결손금의 이월공제는 반영하지 않습니다."
                ),
            )
        )

    separate_allowed = 0 < other_total <= g.other_separate_threshold
    candidates: list[Taxation] = ["comprehensive"]
    if separate_allowed and inp.other_income_taxation is not OtherIncomeTaxation.COMPREHENSIVE:
        candidates.append("separate")
    if inp.other_income_taxation is OtherIncomeTaxation.SEPARATE:
        if separate_allowed:
            candidates = ["separate"]
        elif other_total > 0:
            warnings.append(
                CalcWarning(
                    code="separate_taxation_not_allowed",
                    message=(
                        f"기타소득금액 합계가 {g.other_separate_threshold:,}원을 넘어 "
                        "분리과세를 선택할 수 없어 종합과세로 계산했습니다."
                    ),
                )
            )

    def run(taxation: Taxation) -> tuple[TaxationOption, TaxResult, PrepaidBreakdown]:
        separate = taxation == "separate"
        extra = business_total + (0 if separate else other_total)
        prepaid = PrepaidBreakdown(
            earned_settled=earned_settled,
            business_withholding=business_wh,
            other_withholding=0 if separate else other_wh,
            interim_prepayment=inp.interim_prepayment,
            total=earned_settled
            + business_wh
            + (0 if separate else other_wh)
            + inp.interim_prepayment,
        )
        result = calculate(_with_prepaid(base, prepaid.total), rules, extra_income=extra)
        # 분리과세: 기타소득금액 × 20%로 과세 종결 (원 미만 절사)
        separate_tax = apply_rate(other_total, g.other_separate_rate) if separate else 0
        separate_local = apply_rate(separate_tax, rules.local_income_tax_rate)
        option = TaxationOption(
            taxation=taxation,
            comprehensive_income_amount=max(result.earned_income_amount + extra, 0),
            determined_tax=result.determined_tax,
            local_income_tax=result.local_income_tax.determined_tax,
            separate_tax=separate_tax,
            separate_local_tax=separate_local,
            total_burden=result.determined_tax
            + result.local_income_tax.determined_tax
            + separate_tax
            + separate_local,
        )
        return option, result, prepaid

    runs = [run(t) for t in candidates]
    option, result, prepaid = min(runs, key=lambda r: (r[0].total_burden, r[0].taxation))
    if len(runs) == 2:
        other_option = next(r[0] for r in runs if r[0] is not option)
        warnings.append(
            CalcWarning(
                code="other_income_taxation_selected",
                message=(
                    f"기타소득은 {'분리과세' if option.taxation == 'separate' else '종합과세'}가 "
                    f"{other_option.total_burden - option.total_burden:,}원 유리해 선택했습니다."
                ),
                level=WarningLevel.INFO,
            )
        )

    separate_chosen = option.taxation == "separate"
    earned_lines = (
        [
            IncomeLine(
                kind="earned",
                name="근로소득",
                revenue=result.gross_salary,
                expenses=result.earned_income_deduction.amount,
                income_amount=result.earned_income_amount,
                withholding_tax=earned_settled,
                note="필요경비 = 근로소득공제, 기납부 = 연말정산 결정세액",
            )
        ]
        if base.gross_salary > 0
        else []
    )
    return GlobalIncomeResult(
        tax_year=inp.tax_year,
        rules_verified=rules.verified,
        income_lines=tuple(earned_lines + business + others),
        earned_income_amount=result.earned_income_amount,
        business_income_amount=business_total,
        other_income_amount=0 if separate_chosen else other_total,
        comprehensive_income_amount=option.comprehensive_income_amount,
        other_income_taxation=option.taxation if other_total > 0 else "none",
        separate_tax=option.separate_tax,
        options=tuple(r[0] for r in runs),
        prepaid=prepaid,
        tax_result=result,
        total_balance_due=result.total_balance_due,
        warnings=tuple(warnings) + result.warnings,
        disclaimer=GLOBAL_DISCLAIMER,
    )
