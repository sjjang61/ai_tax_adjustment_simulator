"""사업자(공동사업장) 소득 배분 (순수 함수).

공동사업장은 사업장 단위로 소득금액(총수입금액 − 필요경비)을 계산한 뒤 손익분배비율대로 공동사업자에게
분배한다 (소득세법 제43조). 원천징수세액도 같은 비율로 나눈다.

배분: 각 금액 × 지분 / 지분 합계를 원 미만 절사하고, 남는 끝수는 마지막 사업자에게 준다
(배분 합계가 사업장 금액과 항상 일치).
"""

from decimal import ROUND_DOWN, Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.tax.global_income import BusinessIncome, ExpenseMethod, business_line
from app.tax.inputs import Won
from app.tax.rules.base import TaxRules

MAX_PARTNERS = 10


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Partner(_Model):
    name: str = Field(min_length=1, max_length=50)
    share: int = Field(ge=1, le=1_000_000, description="손익분배비율 지분 (예: 6:4면 6과 4)")
    simulation_id: int | None = Field(
        default=None, description="이 사업자의 연말정산 시뮬레이션 (근로소득)"
    )


class BusinessRecord(_Model):
    """사업자 소득관리 레코드 (사업장 단위)."""

    name: str = Field(min_length=1, max_length=50)
    tax_year: int = Field(ge=2000, le=2100)
    revenue: Won
    expense_method: ExpenseMethod = ExpenseMethod.BOOK
    expenses: Won = 0
    expense_rate: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    withholding_tax: Won | None = Field(
        default=None, description="사업장 전체 원천징수세액. 비우면 총수입금액 × 3%로 추정"
    )
    partners: tuple[Partner, ...] = Field(min_length=1, max_length=MAX_PARTNERS)

    @model_validator(mode="after")
    def _unique_links(self) -> Self:
        linked = [p.simulation_id for p in self.partners if p.simulation_id is not None]
        if len(linked) != len(set(linked)):
            raise ValueError("같은 연말정산 시뮬레이션을 여러 사업자에 연결할 수 없습니다.")
        return self


class PartnerShare(_Model):
    name: str
    share: int
    ratio: str  # 표시용 "60%"
    simulation_id: int | None
    revenue: int
    expenses: int
    income_amount: int
    withholding_tax: int
    business_income: BusinessIncome  # 종합소득세 입력에 그대로 넣을 수 있는 이 사업자 몫


class BusinessAllocation(_Model):
    name: str
    tax_year: int
    revenue: int
    expenses: int
    income_amount: int
    withholding_tax: int
    expense_note: str
    partners: tuple[PartnerShare, ...]


def _split(amount: int, shares: list[int]) -> list[int]:
    """금액을 지분대로 나눈다: 원 미만 절사, 끝수는 마지막에."""
    total = sum(shares)
    parts = [amount * s // total for s in shares[:-1]]
    return [*parts, amount - sum(parts)]


def _ratio(share: int, total: int) -> str:
    pct = (Decimal(share) * 100 / Decimal(total)).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    return f"{pct.normalize():f}%"


def allocate(record: BusinessRecord, rules: TaxRules) -> BusinessAllocation:
    # 사업장 단위 소득금액 (경비율·원천징수 추정 포함) — 종합소득세와 같은 계산 함수 사용
    line = business_line(
        BusinessIncome(
            name=record.name,
            revenue=record.revenue,
            expense_method=record.expense_method,
            expenses=record.expenses,
            expense_rate=record.expense_rate,
            withholding_tax=record.withholding_tax,
        ),
        rules,
    )
    shares = [p.share for p in record.partners]
    total_share = sum(shares)
    revenues = _split(line.revenue, shares)
    expenses = _split(line.expenses, shares)
    withholdings = _split(line.withholding_tax, shares)

    partners = []
    for i, p in enumerate(record.partners):
        ratio = _ratio(p.share, total_share)
        partners.append(
            PartnerShare(
                name=p.name,
                share=p.share,
                ratio=ratio,
                simulation_id=p.simulation_id,
                revenue=revenues[i],
                expenses=expenses[i],
                income_amount=revenues[i] - expenses[i],
                withholding_tax=withholdings[i],
                business_income=BusinessIncome(
                    name=f"{record.name} (지분 {ratio})"[:50],
                    revenue=revenues[i],
                    # 사업장 단위로 계산한 필요경비를 나눈 금액이므로 장부 방식으로 전달한다
                    expense_method=ExpenseMethod.BOOK,
                    expenses=expenses[i],
                    withholding_tax=withholdings[i],
                ),
            )
        )
    return BusinessAllocation(
        name=record.name,
        tax_year=record.tax_year,
        revenue=line.revenue,
        expenses=line.expenses,
        income_amount=line.income_amount,
        withholding_tax=line.withholding_tax,
        expense_note=line.note,
        partners=tuple(partners),
    )
