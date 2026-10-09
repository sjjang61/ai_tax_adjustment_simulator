"""사업자 소득관리 유스케이스: 저장·조회, 지분 배분, 공동사업자 일괄 종합소득세 계산."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models.business import Business
from app.models.simulation import Simulation
from app.schemas.business import (
    BusinessRead,
    BusinessSummary,
    PartnerResult,
    PartnershipResult,
)
from app.tax.business import BusinessAllocation, BusinessRecord, allocate
from app.tax.global_income import GlobalIncomeInput, calculate_global
from app.tax.inputs import Income, SimulationInput, Taxpayer
from app.tax.rules import get_rules

# 연말정산이 연결되지 않은 사업자의 기본 입력: 근로소득 없음, 본인 기본공제만
DEFAULT_BIRTH_YEAR = 1990


def allocate_record(record: BusinessRecord) -> BusinessAllocation:
    return allocate(record, get_rules(record.tax_year))


def _summary(
    b: Business, record: BusinessRecord, allocation: BusinessAllocation
) -> BusinessSummary:
    return BusinessSummary(
        id=b.id,
        name=b.name,
        tax_year=b.tax_year,
        partner_count=len(record.partners),
        income_amount=allocation.income_amount,
        updated_at=b.updated_at,
    )


def _read(b: Business) -> BusinessRead:
    record = BusinessRecord.model_validate(b.record)
    allocation = allocate_record(record)
    return BusinessRead(
        **_summary(b, record, allocation).model_dump(), record=record, allocation=allocation
    )


class BusinessService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _get(self, business_id: int) -> Business:
        b = self.session.get(Business, business_id)
        if b is None:
            raise NotFoundError(f"사업자를 찾을 수 없습니다: {business_id}")
        return b

    def create(self, record: BusinessRecord) -> BusinessRead:
        allocate_record(record)  # 귀속연도 규칙 검증
        b = Business(
            name=record.name, tax_year=record.tax_year, record=record.model_dump(mode="json")
        )
        self.session.add(b)
        self.session.commit()
        self.session.refresh(b)
        return _read(b)

    def list(self, tax_year: int | None = None) -> list[BusinessSummary]:
        stmt = select(Business).order_by(Business.updated_at.desc(), Business.id.desc())
        if tax_year is not None:
            stmt = stmt.where(Business.tax_year == tax_year)
        out = []
        for b in self.session.scalars(stmt).all():
            record = BusinessRecord.model_validate(b.record)
            out.append(_summary(b, record, allocate_record(record)))
        return out

    def get(self, business_id: int) -> BusinessRead:
        return _read(self._get(business_id))

    def update(self, business_id: int, record: BusinessRecord) -> BusinessRead:
        allocate_record(record)
        b = self._get(business_id)
        b.name = record.name
        b.tax_year = record.tax_year
        b.record = record.model_dump(mode="json")
        self.session.commit()
        self.session.refresh(b)
        return _read(b)

    def delete(self, business_id: int) -> None:
        self.session.delete(self._get(business_id))
        self.session.commit()

    def partnership(self, record: BusinessRecord) -> PartnershipResult:
        """공동사업자 각자의 연말정산 결과(근로소득) + 지분만큼의 사업소득으로 종합소득세를 계산한다."""
        rules = get_rules(record.tax_year)
        allocation = allocate(record, rules)
        partners: list[PartnerResult] = []
        for share in allocation.partners:
            notes: list[str] = []
            sim = (
                self.session.get(Simulation, share.simulation_id)
                if share.simulation_id is not None
                else None
            )
            if sim is not None:
                base = SimulationInput.model_validate(sim.input)
                if base.tax_year != record.tax_year:
                    notes.append(
                        f"{base.tax_year}년 귀속 연말정산 결과를 {record.tax_year}년 귀속 계산에 사용했습니다."
                    )
                    base = base.model_copy(update={"tax_year": record.tax_year})
            else:
                if share.simulation_id is not None:
                    notes.append("연결된 연말정산 결과가 삭제되어 근로소득 없이 계산했습니다.")
                else:
                    notes.append(
                        "연말정산 결과가 연결되지 않아 근로소득 없이 계산했습니다 (본인 기본공제만 적용)."
                    )
                base = SimulationInput(
                    tax_year=record.tax_year,
                    income=Income(annual_earned_income=0),
                    taxpayer=Taxpayer(birth_year=DEFAULT_BIRTH_YEAR),
                )
            inp = GlobalIncomeInput(
                tax_year=record.tax_year, base=base, business_incomes=(share.business_income,)
            )
            partners.append(
                PartnerResult(
                    partner=share,
                    simulation_name=sim.name if sim is not None else None,
                    notes=notes,
                    input=inp,
                    result=calculate_global(inp, rules),
                )
            )
        return PartnershipResult(
            allocation=allocation,
            partners=partners,
            combined_total_balance_due=sum(p.result.total_balance_due for p in partners),
        )
