"""테스트 입력 생성 헬퍼."""

from typing import Any

from app.tax.inputs import SimulationInput


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


def input_dict(**override: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "tax_year": 2025,
        "income": {"annual_earned_income": 50_000_000, "non_taxable_income": 0},
        "prepaid_tax": {"withholding": 0, "previous_employer": 0},
        "taxpayer": {"birth_year": 1990},
        "dependents": [],
        "deductions": {},
        "credits": {},
    }
    return _merge(base, override)


def make_input(**override: Any) -> SimulationInput:
    return SimulationInput.model_validate(input_dict(**override))
