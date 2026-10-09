from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Query, status
from fastapi.responses import JSONResponse

from app.api.v1.simulations import ServiceDep
from app.core.errors import ERROR_RESPONSES
from app.schemas.simulation import SimulationExport, SimulationWithWarnings

router = APIRouter(prefix="/simulations", tags=["import-export"], responses=ERROR_RESPONSES)


@router.get(
    "/{simulation_id}/export",
    response_model=SimulationExport,
    summary="시뮬레이션을 JSON 파일로 내보내기",
)
def export_simulation(simulation_id: int, service: ServiceDep) -> JSONResponse:
    doc = service.export(simulation_id)
    filename = f"simulation-{doc.tax_year}-{simulation_id}.json"
    return JSONResponse(
        content=doc.model_dump(mode="json"),
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.post(
    "/import",
    response_model=SimulationWithWarnings,
    status_code=status.HTTP_201_CREATED,
    summary="JSON 파일 가져오기 (target_year 지정 시 연도 이월 변환)",
)
def import_simulation(
    body: SimulationExport,
    service: ServiceDep,
    target_year: Annotated[int | None, Query(ge=2000, le=2100)] = None,
) -> SimulationWithWarnings:
    return service.import_document(body, target_year)
