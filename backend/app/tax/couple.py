"""맞벌이 부부 부양가족 배분 최적화 (순수 함수).

세법상 부양가족 1명은 부부 중 한 사람만 기본공제를 받을 수 있고(중복공제 불가), 그 가족의 의료비·
교육비 공제와 자녀세액공제도 기본공제를 받는 사람이 받는다. 따라서 "부양가족 + 그 가족의 의료비·
교육비"를 배분 단위로 보고, 가능한 모든 배분을 계산 엔진으로 계산해 부부 합산 세액이 가장 적은 안을 찾는다.

- 목적함수: 부부 합산 차감징수세액(지방소득세 포함). 기납부세액은 배분과 무관하므로 합산 세부담 최소와 같다.
- 동률이면 사용자의 현재 배분에서 덜 바뀌는 안을 고른다.
"""

from enum import StrEnum
from itertools import product
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.tax.engine import calculate
from app.tax.inputs import (
    BirthYear,
    Dependent,
    EducationExpense,
    EducationKind,
    Relation,
    SimulationInput,
    Won,
)
from app.tax.result import TaxResult
from app.tax.rules.base import TaxRules

# 2^N 조합을 모두 계산하므로 공유 부양가족 수를 제한한다 (10명 → 1,024개 배분).
MAX_SHARED_DEPENDENTS = 10
MAX_ALTERNATIVES = 3


class Spouse(StrEnum):
    PRIMARY = "primary"  # 본인
    SPOUSE = "spouse"  # 배우자


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SharedDependent(_Model):
    """부부 중 누가 공제받을지 정할 부양가족과 그 가족을 위해 지출한 의료비·교육비."""

    name: str = Field(default="", max_length=50)
    relation: Relation
    birth_year: BirthYear
    disabled: bool = False
    income_amount: Won = 0
    income_is_salary_only: bool = False
    born_or_adopted_this_year: bool = False
    child_order: int | None = Field(default=None, ge=1, le=20)
    medical_expense: Won = Field(default=0, description="이 가족을 위해 지출한 의료비")
    education_kind: EducationKind | None = None
    education_amount: Won = 0
    assigned_to: Spouse = Field(default=Spouse.PRIMARY, description="현재 공제받을 예정인 사람")

    @model_validator(mode="after")
    def _check(self) -> Self:
        if self.relation is Relation.SPOUSE:
            raise ValueError("배우자는 공유 부양가족으로 입력할 수 없습니다 (각자 본인으로 입력).")
        if self.education_kind is EducationKind.SELF:
            raise ValueError("본인 교육비는 각자의 세액공제 단계에서 입력하세요.")
        return self


class CoupleInput(_Model):
    tax_year: int = Field(ge=2000, le=2100)
    primary: SimulationInput
    spouse: SimulationInput
    shared_dependents: tuple[SharedDependent, ...] = Field(
        default=(), max_length=MAX_SHARED_DEPENDENTS
    )

    @model_validator(mode="after")
    def _same_year(self) -> Self:
        if not (self.primary.tax_year == self.spouse.tax_year == self.tax_year):
            raise ValueError("본인·배우자 입력의 귀속연도가 같아야 합니다.")
        return self


class PlanSummary(_Model):
    assignment: tuple[Spouse, ...]
    primary_determined_tax: int
    spouse_determined_tax: int
    combined_determined_tax: int
    combined_local_income_tax: int
    primary_total_balance_due: int
    spouse_total_balance_due: int
    combined_total_balance_due: int


class CoupleOptimizationResult(_Model):
    tax_year: int
    baseline: PlanSummary
    best: PlanSummary
    saving: int = Field(description="현재 배분 대비 최적 배분의 부부 합산 절세액 (지방소득세 포함)")
    alternatives: tuple[PlanSummary, ...]
    evaluated_count: int
    best_primary_input: SimulationInput
    best_spouse_input: SimulationInput
    best_primary_result: TaxResult
    best_spouse_result: TaxResult


MedicalCategory = Literal["specific", "general"]


def medical_category(dep: SharedDependent, tax_year: int, rules: TaxRules) -> MedicalCategory:
    """의료비 구분: 65세 이상·과세기간 개시일 현재 6세 이하·장애인은 한도 없는 특정 의료비."""
    m = rules.medical_credit
    age = tax_year - dep.birth_year  # 세법상 연령 (과세기간 중 도래 나이)
    age_at_start = age - 1  # 과세기간 개시일(1월 1일) 현재 연령
    if dep.disabled or age >= m.specific_min_age or age_at_start <= m.specific_max_age_at_start:
        return "specific"
    return "general"


def build_individual(
    base: SimulationInput, deps: list[SharedDependent], tax_year: int, rules: TaxRules
) -> SimulationInput:
    """배정된 부양가족과 그 가족의 의료비·교육비를 개인 입력에 더한다 (원본 불변)."""
    data = base.model_dump(mode="json")
    medical = data["credits"]["medical"]
    for dep in deps:
        data["dependents"].append(
            Dependent(
                name=dep.name,
                relation=dep.relation,
                birth_year=dep.birth_year,
                disabled=dep.disabled,
                income_amount=dep.income_amount,
                income_is_salary_only=dep.income_is_salary_only,
                born_or_adopted_this_year=dep.born_or_adopted_this_year,
                child_order=dep.child_order,
            ).model_dump(mode="json")
        )
        medical[medical_category(dep, tax_year, rules)] += dep.medical_expense
        if dep.education_kind is not None and dep.education_amount > 0:
            data["credits"]["education"].append(
                EducationExpense(
                    kind=dep.education_kind, amount=dep.education_amount, label=dep.name
                ).model_dump(mode="json")
            )
    return SimulationInput.model_validate(data)


def _split(
    couple: CoupleInput, assignment: tuple[Spouse, ...]
) -> tuple[list[SharedDependent], list[SharedDependent]]:
    primary = [
        d for d, a in zip(couple.shared_dependents, assignment, strict=True) if a is Spouse.PRIMARY
    ]
    spouse = [
        d for d, a in zip(couple.shared_dependents, assignment, strict=True) if a is Spouse.SPOUSE
    ]
    return primary, spouse


def _summary(assignment: tuple[Spouse, ...], p: TaxResult, s: TaxResult) -> PlanSummary:
    return PlanSummary(
        assignment=assignment,
        primary_determined_tax=p.determined_tax,
        spouse_determined_tax=s.determined_tax,
        combined_determined_tax=p.determined_tax + s.determined_tax,
        combined_local_income_tax=(
            p.local_income_tax.determined_tax + s.local_income_tax.determined_tax
        ),
        primary_total_balance_due=p.total_balance_due,
        spouse_total_balance_due=s.total_balance_due,
        combined_total_balance_due=p.total_balance_due + s.total_balance_due,
    )


def evaluate_assignment(
    couple: CoupleInput, assignment: tuple[Spouse, ...], rules: TaxRules
) -> PlanSummary:
    p_deps, s_deps = _split(couple, assignment)
    p = calculate(build_individual(couple.primary, p_deps, couple.tax_year, rules), rules)
    s = calculate(build_individual(couple.spouse, s_deps, couple.tax_year, rules), rules)
    return _summary(assignment, p, s)


def optimize(couple: CoupleInput, rules: TaxRules) -> CoupleOptimizationResult:
    n = len(couple.shared_dependents)
    year = couple.tax_year
    # 각 배우자의 결과는 자기에게 배정된 부분집합에만 의존하므로 부분집합별로 1회만 계산한다.
    cache: dict[tuple[Spouse, frozenset[int]], TaxResult] = {}

    def result_for(who: Spouse, indices: frozenset[int]) -> TaxResult:
        key = (who, indices)
        if key not in cache:
            base = couple.primary if who is Spouse.PRIMARY else couple.spouse
            deps = [couple.shared_dependents[i] for i in sorted(indices)]
            cache[key] = calculate(build_individual(base, deps, year, rules), rules)
        return cache[key]

    def plan(assignment: tuple[Spouse, ...]) -> PlanSummary:
        p_idx = frozenset(i for i, a in enumerate(assignment) if a is Spouse.PRIMARY)
        s_idx = frozenset(range(n)) - p_idx
        return _summary(
            assignment, result_for(Spouse.PRIMARY, p_idx), result_for(Spouse.SPOUSE, s_idx)
        )

    baseline_assignment = tuple(d.assigned_to for d in couple.shared_dependents)

    def moves(assignment: tuple[Spouse, ...]) -> int:
        return sum(a is not b for a, b in zip(assignment, baseline_assignment, strict=True))

    plans = [plan(a) for a in product((Spouse.PRIMARY, Spouse.SPOUSE), repeat=n)]
    plans.sort(key=lambda p: (p.combined_total_balance_due, moves(p.assignment)))
    best = plans[0]
    baseline = plan(baseline_assignment)

    p_idx = frozenset(i for i, a in enumerate(best.assignment) if a is Spouse.PRIMARY)
    p_deps, s_deps = _split(couple, best.assignment)
    return CoupleOptimizationResult(
        tax_year=year,
        baseline=baseline,
        best=best,
        saving=baseline.combined_total_balance_due - best.combined_total_balance_due,
        alternatives=tuple(plans[1 : 1 + MAX_ALTERNATIVES]),
        evaluated_count=len(plans),
        best_primary_input=build_individual(couple.primary, p_deps, year, rules),
        best_spouse_input=build_individual(couple.spouse, s_deps, year, rules),
        best_primary_result=result_for(Spouse.PRIMARY, p_idx),
        best_spouse_result=result_for(Spouse.SPOUSE, frozenset(range(n)) - p_idx),
    )
