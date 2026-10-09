"""종합소득세 시뮬레이션 API 스키마."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.tax.global_income import GlobalIncomeInput, GlobalIncomeResult


class _Schema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GlobalIncomeSimulationCreate(_Schema):
    name: str = Field(min_length=1, max_length=100)
    input: GlobalIncomeInput
    source_simulation_id: int | None = Field(
        default=None, description="불러온 연말정산 시뮬레이션 id"
    )


class GlobalIncomeSimulationUpdate(_Schema):
    name: str = Field(min_length=1, max_length=100)
    input: GlobalIncomeInput


class GlobalIncomeSimulationSummary(_Schema):
    id: int
    name: str
    tax_year: int
    total_balance_due: int
    source_simulation_id: int | None
    created_at: datetime
    updated_at: datetime


class GlobalIncomeSimulationRead(GlobalIncomeSimulationSummary):
    input: GlobalIncomeInput
    result: GlobalIncomeResult
