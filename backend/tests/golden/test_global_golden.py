"""종합소득세 검증 사례 (global_cases/*.json)."""

import json
from pathlib import Path
from typing import Any

import pytest

from app.tax.global_income import GlobalIncomeInput, calculate_global
from app.tax.rules import get_rules

CASES = sorted((Path(__file__).parent / "global_cases").glob("*.json"))


def _check(actual: Any, expected: Any, path: str) -> None:
    if isinstance(expected, dict):
        for key, value in expected.items():
            _check(actual[key], value, f"{path}.{key}")
    else:
        assert actual == expected, path


@pytest.mark.parametrize("path", CASES, ids=[p.stem for p in CASES])
def test_global_golden_case(path: Path) -> None:
    case: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    assert case.get("source")
    inp = GlobalIncomeInput.model_validate(case["input"])
    result = calculate_global(inp, get_rules(inp.tax_year)).model_dump(mode="json")
    _check(result, case["expected"], path.stem)
