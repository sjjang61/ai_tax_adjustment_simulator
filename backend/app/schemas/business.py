"""사업자 소득관리 API 스키마."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.tax.business import BusinessAllocation, BusinessRecord, PartnerShare
from app.tax.global_income import GlobalIncomeInput, GlobalIncomeResult


class _Schema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BusinessSave(_Schema):
    record: BusinessRecord


class BusinessSummary(_Schema):
    id: int
    name: str
    tax_year: int
    partner_count: int
    income_amount: int
    updated_at: datetime


class BusinessRead(BusinessSummary):
    record: BusinessRecord
    allocation: BusinessAllocation


class PartnerResult(_Schema):
    partner: PartnerShare
    simulation_name: str | None
    notes: list[str]
    input: GlobalIncomeInput
    result: GlobalIncomeResult


class PartnershipResult(_Schema):
    allocation: BusinessAllocation
    partners: list[PartnerResult]
    combined_total_balance_due: int
