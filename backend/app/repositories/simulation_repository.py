"""시뮬레이션 DB 접근 계층."""

from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.simulation import Simulation


class SimulationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(
        self,
        *,
        name: str,
        tax_year: int,
        schema_version: int,
        input_data: dict[str, Any],
        result_snapshot: dict[str, Any],
        source_simulation_id: int | None = None,
    ) -> Simulation:
        sim = Simulation(
            name=name,
            tax_year=tax_year,
            schema_version=schema_version,
            input=input_data,
            result_snapshot=result_snapshot,
            source_simulation_id=source_simulation_id,
        )
        self.session.add(sim)
        self.session.commit()
        self.session.refresh(sim)
        return sim

    def get(self, simulation_id: int) -> Simulation | None:
        return self.session.get(Simulation, simulation_id)

    def list(self, tax_year: int | None = None) -> Sequence[Simulation]:
        stmt = select(Simulation).order_by(Simulation.updated_at.desc(), Simulation.id.desc())
        if tax_year is not None:
            stmt = stmt.where(Simulation.tax_year == tax_year)
        return self.session.scalars(stmt).all()

    def update(
        self,
        sim: Simulation,
        *,
        name: str,
        tax_year: int,
        schema_version: int,
        input_data: dict[str, Any],
        result_snapshot: dict[str, Any],
    ) -> Simulation:
        sim.name = name
        sim.tax_year = tax_year
        sim.schema_version = schema_version
        sim.input = input_data
        sim.result_snapshot = result_snapshot
        self.session.commit()
        self.session.refresh(sim)
        return sim

    def delete(self, sim: Simulation) -> None:
        self.session.delete(sim)
        self.session.commit()
