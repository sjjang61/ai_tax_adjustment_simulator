"""시뮬레이션 API 요청/응답 스키마."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.tax.compare import ComparisonResult
from app.tax.inputs import SimulationInput
from app.tax.result import CalcWarning, TaxResult

CURRENT_SCHEMA_VERSION = 1


class _Schema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SimulationCreate(_Schema):
    name: str = Field(min_length=1, max_length=100)
    input: SimulationInput


class SimulationUpdate(SimulationCreate):
    pass


class SimulationSummary(_Schema):
    id: int
    name: str
    tax_year: int
    schema_version: int
    determined_tax: int
    total_balance_due: int
    source_simulation_id: int | None
    created_at: datetime
    updated_at: datetime


class SimulationRead(SimulationSummary):
    input: SimulationInput
    result: TaxResult


class SimulationWithWarnings(_Schema):
    simulation: SimulationRead
    warnings: list[CalcWarning]


class SimulationComparison(_Schema):
    """저장본(기준)과 변경안 비교. 기준 결과는 현재 규칙으로 다시 계산한 값이다."""

    base: SimulationSummary
    snapshot_differs: bool = Field(
        description="저장 당시 결과 스냅샷과 현재 규칙으로 다시 계산한 기준 결과가 다른지 (세법 규칙 변경 등)"
    )
    comparison: ComparisonResult


class SimulationExport(_Schema):
    """JSON 내보내기/가져오기 문서."""

    schema_version: int = Field(ge=1)
    tax_year: int
    name: str = Field(min_length=1, max_length=100)
    exported_at: datetime | None = None
    input: dict[str, Any]


class RulesYears(_Schema):
    supported_years: list[int]
    default_tax_year: int
