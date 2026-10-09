from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.errors import ERROR_RESPONSES
from app.db import get_session
from app.schemas.simulation import (
    SimulationComparison,
    SimulationCreate,
    SimulationRead,
    SimulationSummary,
    SimulationUpdate,
    SimulationWithWarnings,
)
from app.services.simulation_service import SimulationService, calculate_input
from app.tax.inputs import SimulationInput
from app.tax.result import TaxResult

router = APIRouter(prefix="/simulations", tags=["simulations"], responses=ERROR_RESPONSES)


def get_service(session: Annotated[Session, Depends(get_session)]) -> SimulationService:
    return SimulationService(session)


ServiceDep = Annotated[SimulationService, Depends(get_service)]


@router.post("/calculate", response_model=TaxResult, summary="저장 없이 계산 (실시간 미리보기)")
def calculate_simulation(body: SimulationInput) -> TaxResult:
    return calculate_input(body)


@router.post("", response_model=SimulationRead, status_code=status.HTTP_201_CREATED)
def create_simulation(body: SimulationCreate, service: ServiceDep) -> SimulationRead:
    return service.create(body.name, body.input)


@router.get("", response_model=list[SimulationSummary])
def list_simulations(
    service: ServiceDep, tax_year: Annotated[int | None, Query()] = None
) -> list[SimulationSummary]:
    return service.list(tax_year)


@router.get("/{simulation_id}", response_model=SimulationRead)
def get_simulation(simulation_id: int, service: ServiceDep) -> SimulationRead:
    return service.get(simulation_id)


@router.put("/{simulation_id}", response_model=SimulationRead)
def update_simulation(
    simulation_id: int, body: SimulationUpdate, service: ServiceDep
) -> SimulationRead:
    return service.update(simulation_id, body.name, body.input)


@router.delete("/{simulation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_simulation(simulation_id: int, service: ServiceDep) -> Response:
    service.delete(simulation_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{simulation_id}/compare",
    response_model=SimulationComparison,
    summary="저장본(기준)과 변경안 비교 (저장하지 않음)",
)
def compare_simulation(
    simulation_id: int, body: SimulationInput, service: ServiceDep
) -> SimulationComparison:
    return service.compare(simulation_id, body)


@router.post(
    "/{simulation_id}/carry-over",
    response_model=SimulationWithWarnings,
    status_code=status.HTTP_201_CREATED,
    summary="전년도 시뮬레이션으로 올해 초안 생성",
)
def carry_over_simulation(
    simulation_id: int,
    service: ServiceDep,
    target_year: Annotated[int, Query(ge=2000, le=2100)],
    salary_increase_rate: Annotated[
        Decimal | None, Query(ge=-50, le=100, description="급여 인상률(%)")
    ] = None,
) -> SimulationWithWarnings:
    return service.carry_over(simulation_id, target_year, salary_increase_rate)
