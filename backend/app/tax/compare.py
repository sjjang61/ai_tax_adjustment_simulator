"""두 계산 결과 비교 (순수 함수): 저장본(기준) vs 변경안.

차이는 모두 계산 엔진 결과끼리의 차이다. 입력 차이는 JSON 경로(예: ``dependents[0].birth_year``)로 표현한다.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict

from app.tax.inputs import SimulationInput
from app.tax.result import BreakdownItem, TaxResult


class _Output(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class MetricDiff(_Output):
    key: str
    label: str
    before: int
    after: int
    delta: int


class ItemDiff(_Output):
    key: str
    label: str
    before: int
    after: int
    delta: int


class InputDiff(_Output):
    path: str
    before: Any
    after: Any


class ComparisonResult(_Output):
    before: TaxResult
    after: TaxResult
    saving: int  # 양수 = 변경안이 유리 (부담 감소 또는 환급 증가, 지방소득세 포함)
    tax_year_changed: bool
    metrics: tuple[MetricDiff, ...]
    income_deduction_diffs: tuple[ItemDiff, ...]
    tax_credit_diffs: tuple[ItemDiff, ...]
    input_diffs: tuple[InputDiff, ...]


_METRICS: tuple[tuple[str, str], ...] = (
    ("gross_salary", "총급여"),
    ("earned_income_amount", "근로소득금액"),
    ("total_income_deduction", "소득공제 합계"),
    ("tax_base", "과세표준"),
    ("calculated_tax", "산출세액"),
    ("total_tax_credit", "세액공제 합계"),
    ("determined_tax", "결정세액"),
    ("local_income_tax", "지방소득세"),
    ("prepaid_tax", "기납부세액"),
    ("total_balance_due", "정산 결과 (지방소득세 포함, 음수 = 환급)"),
)


def _metric_value(result: TaxResult, key: str) -> int:
    if key == "local_income_tax":
        return result.local_income_tax.determined_tax
    value = getattr(result, key)
    assert isinstance(value, int)
    return value


def _flatten_items(items: tuple[BreakdownItem, ...]) -> dict[str, BreakdownItem]:
    out: dict[str, BreakdownItem] = {}
    for item in items:
        out[item.key] = item
        out.update(_flatten_items(item.children))
    return out


def _item_diffs(
    before: tuple[BreakdownItem, ...], after: tuple[BreakdownItem, ...]
) -> tuple[ItemDiff, ...]:
    b, a = _flatten_items(before), _flatten_items(after)
    diffs: list[ItemDiff] = []
    for key in list(b) + [k for k in a if k not in b]:  # 기준 순서 유지, 새 항목은 뒤에
        before_amount = b[key].amount if key in b else 0
        after_amount = a[key].amount if key in a else 0
        if before_amount != after_amount:
            label = (a.get(key) or b[key]).label
            diffs.append(
                ItemDiff(
                    key=key,
                    label=label,
                    before=before_amount,
                    after=after_amount,
                    delta=after_amount - before_amount,
                )
            )
    return tuple(diffs)


def diff_inputs(before: Any, after: Any, path: str = "") -> list[InputDiff]:
    """두 입력(JSON 형태)의 차이를 경로별로 나열한다. 리스트는 index로 비교한다."""
    if isinstance(before, dict) and isinstance(after, dict):
        diffs: list[InputDiff] = []
        for key in list(before) + [k for k in after if k not in before]:
            sub = f"{path}.{key}" if path else str(key)
            diffs += diff_inputs(before.get(key), after.get(key), sub)
        return diffs
    if isinstance(before, list) and isinstance(after, list):
        diffs = []
        for i in range(max(len(before), len(after))):
            sub = f"{path}[{i}]"
            if i >= len(before):
                diffs.append(InputDiff(path=sub, before=None, after=after[i]))
            elif i >= len(after):
                diffs.append(InputDiff(path=sub, before=before[i], after=None))
            else:
                diffs += diff_inputs(before[i], after[i], sub)
        return diffs
    return [] if before == after else [InputDiff(path=path, before=before, after=after)]


def compare(
    before_input: SimulationInput,
    before: TaxResult,
    after_input: SimulationInput,
    after: TaxResult,
) -> ComparisonResult:
    metrics = tuple(
        MetricDiff(
            key=key,
            label=label,
            before=_metric_value(before, key),
            after=_metric_value(after, key),
            delta=_metric_value(after, key) - _metric_value(before, key),
        )
        for key, label in _METRICS
    )
    return ComparisonResult(
        before=before,
        after=after,
        saving=before.total_balance_due - after.total_balance_due,
        tax_year_changed=before.tax_year != after.tax_year,
        metrics=metrics,
        income_deduction_diffs=_item_diffs(before.income_deductions, after.income_deductions),
        tax_credit_diffs=_item_diffs(before.tax_credits, after.tax_credits),
        input_diffs=tuple(
            diff_inputs(before_input.model_dump(mode="json"), after_input.model_dump(mode="json"))
        ),
    )
