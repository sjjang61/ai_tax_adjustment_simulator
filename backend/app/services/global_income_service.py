"""종합소득세 시뮬레이션 유스케이스: 계산, 저장, 불러오기."""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models.global_income import GlobalIncomeSimulation
from app.models.simulation import Simulation
from app.schemas.global_income import (
    GlobalIncomeSimulationRead,
    GlobalIncomeSimulationSummary,
)
from app.tax.global_income import GlobalIncomeInput, GlobalIncomeResult, calculate_global
from app.tax.rules import get_rules


def calculate_global_input(inp: GlobalIncomeInput) -> GlobalIncomeResult:
    return calculate_global(inp, get_rules(inp.tax_year))


def _summary(sim: GlobalIncomeSimulation) -> GlobalIncomeSimulationSummary:
    return GlobalIncomeSimulationSummary(
        id=sim.id,
        name=sim.name,
        tax_year=sim.tax_year,
        total_balance_due=int(sim.result_snapshot.get("total_balance_due", 0)),
        source_simulation_id=sim.source_simulation_id,
        created_at=sim.created_at,
        updated_at=sim.updated_at,
    )


def _read(sim: GlobalIncomeSimulation) -> GlobalIncomeSimulationRead:
    return GlobalIncomeSimulationRead(
        **_summary(sim).model_dump(),
        input=GlobalIncomeInput.model_validate(sim.input),
        result=GlobalIncomeResult.model_validate(sim.result_snapshot),
    )


class GlobalIncomeService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _get(self, sim_id: int) -> GlobalIncomeSimulation:
        sim = self.session.get(GlobalIncomeSimulation, sim_id)
        if sim is None:
            raise NotFoundError(f"종합소득세 시뮬레이션을 찾을 수 없습니다: {sim_id}")
        return sim

    def create(
        self, name: str, inp: GlobalIncomeInput, source_simulation_id: int | None
    ) -> GlobalIncomeSimulationRead:
        if (
            source_simulation_id is not None
            and self.session.get(Simulation, source_simulation_id) is None
        ):
            source_simulation_id = None  # 원본이 없으면 연결하지 않는다
        result = calculate_global_input(inp)
        sim = GlobalIncomeSimulation(
            name=name,
            tax_year=inp.tax_year,
            input=inp.model_dump(mode="json"),
            result_snapshot=result.model_dump(mode="json"),
            source_simulation_id=source_simulation_id,
        )
        self.session.add(sim)
        self.session.commit()
        self.session.refresh(sim)
        return _read(sim)

    def list(self, tax_year: int | None = None) -> list[GlobalIncomeSimulationSummary]:
        stmt = select(GlobalIncomeSimulation).order_by(
            GlobalIncomeSimulation.updated_at.desc(), GlobalIncomeSimulation.id.desc()
        )
        if tax_year is not None:
            stmt = stmt.where(GlobalIncomeSimulation.tax_year == tax_year)
        rows: Sequence[GlobalIncomeSimulation] = self.session.scalars(stmt).all()
        return [_summary(s) for s in rows]

    def get(self, sim_id: int) -> GlobalIncomeSimulationRead:
        return _read(self._get(sim_id))

    def update(self, sim_id: int, name: str, inp: GlobalIncomeInput) -> GlobalIncomeSimulationRead:
        sim = self._get(sim_id)
        sim.name = name
        sim.tax_year = inp.tax_year
        sim.input = inp.model_dump(mode="json")
        sim.result_snapshot = calculate_global_input(inp).model_dump(mode="json")
        self.session.commit()
        self.session.refresh(sim)
        return _read(sim)

    def delete(self, sim_id: int) -> None:
        self.session.delete(self._get(sim_id))
        self.session.commit()
