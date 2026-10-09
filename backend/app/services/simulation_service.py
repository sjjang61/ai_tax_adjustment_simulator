"""시뮬레이션 유스케이스: 계산, 저장, 불러오기, 연도 이월, 가져오기/내보내기."""

from datetime import UTC, datetime
from decimal import Decimal

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.errors import AppError, NotFoundError
from app.models.simulation import Simulation
from app.repositories.simulation_repository import SimulationRepository
from app.schemas.simulation import (
    CURRENT_SCHEMA_VERSION,
    SimulationComparison,
    SimulationExport,
    SimulationRead,
    SimulationSummary,
    SimulationWithWarnings,
)
from app.services.carry_over import CarryOverError, carry_over
from app.services.schema_migration import SchemaVersionError, migrate_input
from app.tax.compare import compare
from app.tax.engine import calculate
from app.tax.inputs import SimulationInput
from app.tax.result import CalcWarning, TaxResult
from app.tax.rules import get_rules


def calculate_input(inp: SimulationInput) -> TaxResult:
    return calculate(inp, get_rules(inp.tax_year))


def _to_summary(sim: Simulation) -> SimulationSummary:
    snapshot = sim.result_snapshot
    return SimulationSummary(
        id=sim.id,
        name=sim.name,
        tax_year=sim.tax_year,
        schema_version=sim.schema_version,
        determined_tax=int(snapshot.get("determined_tax", 0)),
        total_balance_due=int(snapshot.get("total_balance_due", 0)),
        source_simulation_id=sim.source_simulation_id,
        created_at=sim.created_at,
        updated_at=sim.updated_at,
    )


def _to_read(sim: Simulation) -> SimulationRead:
    """저장된 입력은 현재 스키마로 마이그레이션해 검증하고, 결과는 저장 당시 스냅샷을 반환한다."""
    summary = _to_summary(sim)
    return SimulationRead(
        **summary.model_dump(),
        input=SimulationInput.model_validate(migrate_input(sim.input, sim.schema_version)),
        result=TaxResult.model_validate(sim.result_snapshot),
    )


class SimulationService:
    def __init__(self, session: Session) -> None:
        self.repo = SimulationRepository(session)

    def _get(self, simulation_id: int) -> Simulation:
        sim = self.repo.get(simulation_id)
        if sim is None:
            raise NotFoundError(f"시뮬레이션을 찾을 수 없습니다: {simulation_id}")
        return sim

    def create(
        self, name: str, inp: SimulationInput, source_simulation_id: int | None = None
    ) -> SimulationRead:
        result = calculate_input(inp)
        sim = self.repo.add(
            name=name,
            tax_year=inp.tax_year,
            schema_version=CURRENT_SCHEMA_VERSION,
            input_data=inp.model_dump(mode="json"),
            result_snapshot=result.model_dump(mode="json"),
            source_simulation_id=source_simulation_id,
        )
        return _to_read(sim)

    def list(self, tax_year: int | None = None) -> list[SimulationSummary]:
        return [_to_summary(s) for s in self.repo.list(tax_year)]

    def get(self, simulation_id: int) -> SimulationRead:
        return _to_read(self._get(simulation_id))

    def update(self, simulation_id: int, name: str, inp: SimulationInput) -> SimulationRead:
        sim = self._get(simulation_id)
        result = calculate_input(inp)
        sim = self.repo.update(
            sim,
            name=name,
            tax_year=inp.tax_year,
            schema_version=CURRENT_SCHEMA_VERSION,
            input_data=inp.model_dump(mode="json"),
            result_snapshot=result.model_dump(mode="json"),
        )
        return _to_read(sim)

    def delete(self, simulation_id: int) -> None:
        self.repo.delete(self._get(simulation_id))

    def compare(self, simulation_id: int, changed: SimulationInput) -> SimulationComparison:
        """저장본을 기준으로 변경안의 차이를 계산한다. 기준도 현재 규칙으로 다시 계산한다."""
        base = self.get(simulation_id)
        before = calculate_input(base.input)
        after = calculate_input(changed)
        return SimulationComparison(
            base=SimulationSummary(**base.model_dump(exclude={"input", "result"})),
            snapshot_differs=before.model_dump(mode="json") != base.result.model_dump(mode="json"),
            comparison=compare(base.input, before, changed, after),
        )

    def carry_over(
        self, simulation_id: int, target_year: int, salary_increase_rate: Decimal | None
    ) -> SimulationWithWarnings:
        source = self.get(simulation_id)
        try:
            converted = carry_over(
                source.input, target_year, salary_increase_rate=salary_increase_rate
            )
        except CarryOverError as exc:
            raise AppError("invalid_carry_over", str(exc)) from exc
        draft = self.create(
            f"{source.name} → {target_year}년 초안"[:100],
            converted.input,
            source_simulation_id=source.id,
        )
        return SimulationWithWarnings(simulation=draft, warnings=list(converted.warnings))

    def export(self, simulation_id: int) -> SimulationExport:
        sim = self.get(simulation_id)
        return SimulationExport(
            schema_version=CURRENT_SCHEMA_VERSION,
            tax_year=sim.tax_year,
            name=sim.name,
            exported_at=datetime.now(UTC),
            input=sim.input.model_dump(mode="json"),
        )

    def import_document(
        self, doc: SimulationExport, target_year: int | None = None
    ) -> SimulationWithWarnings:
        try:
            migrated = migrate_input(doc.input, doc.schema_version)
        except SchemaVersionError as exc:
            raise AppError(
                "unsupported_schema_version",
                str(exc),
                details={"schema_version": exc.version, "current": CURRENT_SCHEMA_VERSION},
            ) from exc
        try:
            inp = SimulationInput.model_validate(migrated)
        except ValidationError as exc:
            raise AppError(
                "invalid_import",
                "가져온 파일의 입력값이 올바르지 않습니다.",
                status_code=422,
                details={
                    "errors": [
                        {"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]}
                        for e in exc.errors()
                    ]
                },
            ) from exc
        if inp.tax_year != doc.tax_year:
            raise AppError(
                "invalid_import",
                f"문서의 귀속연도({doc.tax_year})와 입력의 귀속연도({inp.tax_year})가 다릅니다.",
            )
        get_rules(inp.tax_year)  # 지원 연도 검증

        warnings: list[CalcWarning] = []
        name = doc.name
        if target_year is not None and target_year != inp.tax_year:
            try:
                converted = carry_over(inp, target_year)
            except CarryOverError as exc:
                raise AppError("invalid_carry_over", str(exc)) from exc
            inp = converted.input
            warnings = list(converted.warnings)
            name = f"{doc.name} → {target_year}년 초안"[:100]
        return SimulationWithWarnings(simulation=self.create(name, inp), warnings=warnings)
