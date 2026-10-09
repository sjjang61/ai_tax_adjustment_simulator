from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.errors import ERROR_RESPONSES
from app.db import get_session
from app.schemas.global_income import (
    GlobalIncomeSimulationCreate,
    GlobalIncomeSimulationRead,
    GlobalIncomeSimulationSummary,
    GlobalIncomeSimulationUpdate,
)
from app.services.global_income_service import GlobalIncomeService, calculate_global_input
from app.tax.global_income import GlobalIncomeInput, GlobalIncomeResult

router = APIRouter(prefix="/global-income", tags=["global-income"], responses=ERROR_RESPONSES)


def get_service(session: Annotated[Session, Depends(get_session)]) -> GlobalIncomeService:
    return GlobalIncomeService(session)


ServiceDep = Annotated[GlobalIncomeService, Depends(get_service)]


@router.post(
    "/calculate",
    response_model=GlobalIncomeResult,
    summary="종합소득세 계산 (근로 + 사업 + 기타소득, 저장하지 않음)",
)
def calculate_global_income(body: GlobalIncomeInput) -> GlobalIncomeResult:
    return calculate_global_input(body)


@router.post(
    "/simulations", response_model=GlobalIncomeSimulationRead, status_code=status.HTTP_201_CREATED
)
def create_global_simulation(
    body: GlobalIncomeSimulationCreate, service: ServiceDep
) -> GlobalIncomeSimulationRead:
    return service.create(body.name, body.input, body.source_simulation_id)


@router.get("/simulations", response_model=list[GlobalIncomeSimulationSummary])
def list_global_simulations(
    service: ServiceDep, tax_year: Annotated[int | None, Query()] = None
) -> list[GlobalIncomeSimulationSummary]:
    return service.list(tax_year)


@router.get("/simulations/{sim_id}", response_model=GlobalIncomeSimulationRead)
def get_global_simulation(sim_id: int, service: ServiceDep) -> GlobalIncomeSimulationRead:
    return service.get(sim_id)


@router.put("/simulations/{sim_id}", response_model=GlobalIncomeSimulationRead)
def update_global_simulation(
    sim_id: int, body: GlobalIncomeSimulationUpdate, service: ServiceDep
) -> GlobalIncomeSimulationRead:
    return service.update(sim_id, body.name, body.input)


@router.delete("/simulations/{sim_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_global_simulation(sim_id: int, service: ServiceDep) -> Response:
    service.delete(sim_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
