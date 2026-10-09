from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.errors import ERROR_RESPONSES
from app.db import get_session
from app.schemas.business import BusinessRead, BusinessSave, BusinessSummary, PartnershipResult
from app.services.business_service import BusinessService, allocate_record
from app.tax.business import BusinessAllocation, BusinessRecord

router = APIRouter(prefix="/businesses", tags=["businesses"], responses=ERROR_RESPONSES)


def get_service(session: Annotated[Session, Depends(get_session)]) -> BusinessService:
    return BusinessService(session)


ServiceDep = Annotated[BusinessService, Depends(get_service)]


@router.post(
    "/allocate",
    response_model=BusinessAllocation,
    summary="사업장 소득금액을 손익분배비율대로 배분 (저장하지 않음)",
)
def allocate_business(body: BusinessRecord) -> BusinessAllocation:
    return allocate_record(body)


@router.post(
    "/partnership",
    response_model=PartnershipResult,
    summary="공동사업자 일괄 종합소득세 계산 (각자의 연말정산 결과 + 지분만큼의 사업소득)",
)
def calculate_partnership(body: BusinessRecord, service: ServiceDep) -> PartnershipResult:
    return service.partnership(body)


@router.post("", response_model=BusinessRead, status_code=status.HTTP_201_CREATED)
def create_business(body: BusinessSave, service: ServiceDep) -> BusinessRead:
    return service.create(body.record)


@router.get("", response_model=list[BusinessSummary])
def list_businesses(
    service: ServiceDep, tax_year: Annotated[int | None, Query()] = None
) -> list[BusinessSummary]:
    return service.list(tax_year)


@router.get("/{business_id}", response_model=BusinessRead)
def get_business(business_id: int, service: ServiceDep) -> BusinessRead:
    return service.get(business_id)


@router.put("/{business_id}", response_model=BusinessRead)
def update_business(business_id: int, body: BusinessSave, service: ServiceDep) -> BusinessRead:
    return service.update(business_id, body.record)


@router.delete("/{business_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_business(business_id: int, service: ServiceDep) -> Response:
    service.delete(business_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
