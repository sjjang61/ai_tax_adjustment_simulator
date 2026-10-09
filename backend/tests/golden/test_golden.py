"""검증된 사례 기반 end-to-end 계산 테스트.

각 사례(cases/*.json)는 입력·기대 결과·출처를 담는다.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from app.tax.engine import calculate
from app.tax.inputs import SimulationInput
from app.tax.rules import get_rules

CASES_DIR = Path(__file__).parent / "cases"
CASES = sorted(CASES_DIR.glob("*.json"))


def _load(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return data


@pytest.mark.parametrize("path", CASES, ids=[p.stem for p in CASES])
def test_golden_case(path: Path) -> None:
    case = _load(path)
    assert case.get("source"), "골든 사례에는 출처가 필요합니다."
    inp = SimulationInput.model_validate(case["input"])
    result = calculate(inp, get_rules(inp.tax_year)).model_dump(mode="json")
    for key, expected in case["expected"].items():
        assert result[key] == expected, f"{path.stem}: {key}"


def test_cases_exist() -> None:
    assert CASES, "골든 사례가 없습니다."
