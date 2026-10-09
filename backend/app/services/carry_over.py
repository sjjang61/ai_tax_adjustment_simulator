"""연도 이월 변환: 전년도 시뮬레이션 입력을 올해 초안으로 변환한다.

- 원본 입력은 변경하지 않고 새 입력 객체를 반환한다.
- 부양가족 나이는 출생연도로 저장되므로 귀속연도만 바꾸면 +1 재계산된다. 이후 요건을 재판정해
  경로우대(70세)·자녀세액공제(8세)·기본공제 나이 요건 변화를 경고로 알린다.
- 귀속연도 사이에 사라지거나 새로 생긴 입력 항목은 ``FIELD_MAPPINGS``로 처리하고,
  매핑할 수 없는 항목은 경고로 반환한다.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.tax.eligibility import PersonStatus, evaluate
from app.tax.inputs import SimulationInput
from app.tax.money import truncate_won
from app.tax.result import CalcWarning, WarningLevel
from app.tax.rules import get_rules


@dataclass(frozen=True)
class FieldMapping:
    """입력 항목 매핑.

    - source와 target이 모두 있으면 값 이동(이름 변경)
    - target이 None이면 올해 규칙에서 사라진 항목: 값을 제거하고 경고
    - source가 None이면 올해 새로 생긴 항목: target에 default를 넣고 안내
    """

    source: str | None
    target: str | None
    note: str
    default: Any = None


# (원본 연도, 다음 연도) → 매핑 목록
FIELD_MAPPINGS: dict[tuple[int, int], tuple[FieldMapping, ...]] = {
    (2025, 2026): (
        FieldMapping(
            source=None,
            target=None,
            note=(
                "2026년 귀속부터 신용카드 등 소득공제 기본한도가 기본공제 대상 자녀 수에 따라 "
                "늘어납니다(자동 반영)."
            ),
        ),
        FieldMapping(
            source=None,
            target="deductions.national_growth_fund",
            note=(
                "2026년 귀속부터 국민성장펀드 소득공제가 신설되었습니다. 전용계좌 납입액이 있으면 "
                "소득공제 단계에서 입력하세요."
            ),
            default=0,
        ),
    ),
}


class CarryOverError(ValueError):
    pass


@dataclass(frozen=True)
class CarryOverResult:
    input: SimulationInput
    warnings: tuple[CalcWarning, ...]


_MISSING = object()


def _get_path(data: dict[str, Any], path: str) -> Any:
    node: Any = data
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return _MISSING
        node = node[part]
    return node


def _pop_path(data: dict[str, Any], path: str) -> Any:
    *parents, last = path.split(".")
    node: Any = data
    for part in parents:
        if not isinstance(node, dict) or part not in node:
            return _MISSING
        node = node[part]
    if not isinstance(node, dict):
        return _MISSING
    return node.pop(last, _MISSING)


def _set_path(data: dict[str, Any], path: str, value: Any) -> None:
    *parents, last = path.split(".")
    node = data
    for part in parents:
        node = node.setdefault(part, {})
    node[last] = value


def _is_empty(value: Any) -> bool:
    return value in (None, 0, False, "", [], {})


def _apply_mappings(
    data: dict[str, Any], mappings: tuple[FieldMapping, ...], to_year: int
) -> list[CalcWarning]:
    warnings: list[CalcWarning] = []
    for m in mappings:
        if m.source is None:
            if m.target is not None and _get_path(data, m.target) is _MISSING:
                _set_path(data, m.target, m.default)
            warnings.append(
                CalcWarning(
                    code="carry_over_new_item",
                    message=m.note,
                    level=WarningLevel.INFO,
                    field=m.target,
                )
            )
            continue
        value = _pop_path(data, m.source)
        if value is _MISSING:
            continue
        if m.target is None:
            if not _is_empty(value):
                warnings.append(
                    CalcWarning(
                        code="carry_over_unmapped",
                        message=f"{to_year}년 귀속에 없는 항목이라 이월하지 않았습니다: {m.note}",
                        field=m.source,
                    )
                )
            continue
        _set_path(data, m.target, value)
        warnings.append(
            CalcWarning(
                code="carry_over_mapped",
                message=m.note,
                level=WarningLevel.INFO,
                field=m.target,
            )
        )
    return warnings


def _status_changes(
    before: tuple[PersonStatus, ...], after: tuple[PersonStatus, ...], target_year: int
) -> list[CalcWarning]:
    warnings: list[CalcWarning] = []
    before_map = {p.dependent_index: p for p in before}
    for new in after:
        old = before_map.get(new.dependent_index)
        field = None if new.dependent_index is None else f"dependents[{new.dependent_index}]"
        if old is None:
            continue
        if old.basic_eligible and not new.basic_eligible:
            warnings.append(
                CalcWarning(
                    code="carry_over_lost_basic",
                    message=(
                        f"{new.label}: {target_year}년 기준 {new.age}세로 기본공제 요건을 "
                        "충족하지 않게 됩니다."
                    ),
                    field=field,
                )
            )
        elif not old.basic_eligible and new.basic_eligible:
            warnings.append(
                CalcWarning(
                    code="carry_over_gained_basic",
                    message=f"{new.label}: {target_year}년 기준 {new.age}세로 기본공제 대상이 됩니다.",
                    level=WarningLevel.INFO,
                    field=field,
                )
            )
        if new.elderly and not old.elderly:
            warnings.append(
                CalcWarning(
                    code="carry_over_elderly",
                    message=f"{new.label}: {new.age}세가 되어 경로우대 추가공제 대상이 됩니다.",
                    level=WarningLevel.INFO,
                    field=field,
                )
            )
        if new.child_credit_eligible and not old.child_credit_eligible:
            warnings.append(
                CalcWarning(
                    code="carry_over_child_credit",
                    message=f"{new.label}: {new.age}세가 되어 자녀세액공제 대상이 됩니다.",
                    level=WarningLevel.INFO,
                    field=field,
                )
            )
        elif old.child_credit_eligible and not new.child_credit_eligible and new.basic_eligible:
            warnings.append(
                CalcWarning(
                    code="carry_over_lost_child_credit",
                    message=f"{new.label}: 자녀세액공제 대상에서 제외됩니다.",
                    field=field,
                )
            )
    return warnings


def carry_over(
    source: SimulationInput,
    target_year: int,
    *,
    salary_increase_rate: Decimal | None = None,
    mappings: Mapping[tuple[int, int], tuple[FieldMapping, ...]] = FIELD_MAPPINGS,
) -> CarryOverResult:
    if target_year <= source.tax_year:
        raise CarryOverError(
            f"이월 대상 연도({target_year})는 원본 연도({source.tax_year})보다 이후여야 합니다."
        )
    source_rules = get_rules(source.tax_year)
    target_rules = get_rules(target_year)

    data = source.model_dump(mode="json")
    warnings: list[CalcWarning] = []

    for year in range(source.tax_year, target_year):
        warnings += _apply_mappings(data, mappings.get((year, year + 1), ()), year + 1)
    data["tax_year"] = target_year

    # 해당 연도에만 적용되는 1회성 항목 초기화
    for i, dep in enumerate(data["dependents"]):
        if dep.get("born_or_adopted_this_year"):
            dep["born_or_adopted_this_year"] = False
            warnings.append(
                CalcWarning(
                    code="carry_over_reset_birth",
                    message="출산·입양 세액공제는 해당 연도에만 적용되어 초기화했습니다.",
                    level=WarningLevel.INFO,
                    field=f"dependents[{i}].born_or_adopted_this_year",
                )
            )
    if data["taxpayer"].get("marriage_registered_this_year"):
        data["taxpayer"]["marriage_registered_this_year"] = False
        warnings.append(
            CalcWarning(
                code="carry_over_reset_marriage",
                message="결혼세액공제는 혼인신고한 해에만 적용되어 초기화했습니다.",
                level=WarningLevel.INFO,
                field="taxpayer.marriage_registered_this_year",
            )
        )

    if salary_increase_rate is not None and salary_increase_rate != 0:
        income = data["income"]
        before = income["annual_earned_income"]
        # 원 미만 절사
        after = truncate_won(Decimal(before) * (1 + salary_increase_rate / 100))
        income["annual_earned_income"] = max(after, income["non_taxable_income"])
        warnings.append(
            CalcWarning(
                code="carry_over_salary_adjusted",
                message=(
                    f"급여 인상률 {salary_increase_rate}%를 적용해 연간 근로소득을 "
                    f"{before:,}원 → {income['annual_earned_income']:,}원으로 조정했습니다."
                ),
                level=WarningLevel.INFO,
                field="income.annual_earned_income",
            )
        )

    prepaid = data["prepaid_tax"]
    if prepaid["withholding"] or prepaid["previous_employer"]:
        warnings.append(
            CalcWarning(
                code="carry_over_prepaid_tax",
                message="기납부세액은 전년도 값입니다. 올해 원천징수 내역으로 수정하세요.",
                level=WarningLevel.INFO,
                field="prepaid_tax",
            )
        )

    target_input = SimulationInput.model_validate(data)
    warnings += _status_changes(
        evaluate(source, source_rules).persons,
        evaluate(target_input, target_rules).persons,
        target_year,
    )
    return CarryOverResult(input=target_input, warnings=tuple(warnings))
