"""저장본(기준) vs 변경안 비교."""

from app.tax.compare import compare, diff_inputs
from app.tax.engine import calculate
from app.tax.inputs import SimulationInput
from app.tax.rules import get_rules
from tests.factories import make_input

BASE = make_input(
    income={"annual_earned_income": 60_000_000},
    prepaid_tax={"withholding": 3_000_000},
    taxpayer={"is_married": True},
    dependents=[{"name": "첫째", "relation": "lineal_descendant", "birth_year": 2012}],
)


def _compare(base: SimulationInput, after: SimulationInput):  # type: ignore[no-untyped-def]
    return compare(
        base,
        calculate(base, get_rules(base.tax_year)),
        after,
        calculate(after, get_rules(after.tax_year)),
    )


def test_identical_inputs_have_no_differences() -> None:
    c = _compare(BASE, BASE)
    assert c.saving == 0
    assert all(m.delta == 0 for m in c.metrics)
    assert c.input_diffs == ()
    assert c.income_deduction_diffs == ()
    assert c.tax_credit_diffs == ()
    assert c.tax_year_changed is False


def test_irp_increase_shows_credit_and_saving() -> None:
    after = BASE.model_copy(update={"credits": BASE.credits.model_copy(update={"irp": 3_000_000})})
    c = _compare(BASE, after)
    # 총급여 6천만원(5,500만원 초과) → 12% = 360,000원 + 지방소득세 36,000원
    assert c.saving == 396_000
    determined = next(m for m in c.metrics if m.key == "determined_tax")
    assert (determined.delta, determined.label) == (-360_000, "결정세액")
    credit = next(d for d in c.tax_credit_diffs if d.key == "pension_account_credit")
    assert (credit.before, credit.after, credit.delta) == (0, 360_000, 360_000)
    assert [(d.path, d.before, d.after) for d in c.input_diffs] == [("credits.irp", 0, 3_000_000)]


def test_metrics_cover_pipeline_in_order() -> None:
    c = _compare(BASE, BASE)
    assert [m.key for m in c.metrics] == [
        "gross_salary",
        "earned_income_amount",
        "total_income_deduction",
        "tax_base",
        "calculated_tax",
        "total_tax_credit",
        "determined_tax",
        "local_income_tax",
        "prepaid_tax",
        "total_balance_due",
    ]


def test_salary_change_affects_nested_breakdown_items() -> None:
    after = BASE.model_copy(
        update={"income": BASE.income.model_copy(update={"annual_earned_income": 70_000_000})}
    )
    c = _compare(BASE, after)
    assert c.saving < 0  # 급여가 오르면 세금도 늘어남
    gross = next(m for m in c.metrics if m.key == "gross_salary")
    assert gross.delta == 10_000_000
    eid_before = c.before.earned_income_deduction.amount
    assert next(m for m in c.metrics if m.key == "earned_income_amount").delta == (
        10_000_000 - (c.after.earned_income_deduction.amount - eid_before)
    )
    assert any(d.path == "income.annual_earned_income" for d in c.input_diffs)


def test_list_diffs_added_removed_and_changed() -> None:
    before = {"dependents": [{"name": "a", "birth_year": 2010}], "x": 1}
    after = {
        "dependents": [{"name": "a", "birth_year": 2011}, {"name": "b", "birth_year": 2015}],
        "x": 1,
    }
    diffs = diff_inputs(before, after)
    assert [(d.path, d.before, d.after) for d in diffs] == [
        ("dependents[0].birth_year", 2010, 2011),
        ("dependents[1]", None, {"name": "b", "birth_year": 2015}),
    ]
    removed = diff_inputs(after, before)
    assert removed[-1].path == "dependents[1]" and removed[-1].after is None


def test_removing_dependent_shows_personal_deduction_drop() -> None:
    after = BASE.model_copy(update={"dependents": ()})
    c = _compare(BASE, after)
    personal = next(d for d in c.income_deduction_diffs if d.key == "personal_deduction")
    assert personal.delta == -1_500_000
    assert any(d.path == "dependents[0]" and d.after is None for d in c.input_diffs)


def test_different_tax_year() -> None:
    after = BASE.model_copy(update={"tax_year": 2026})
    c = _compare(BASE, after)
    assert c.tax_year_changed is True
    assert c.before.tax_year == 2025 and c.after.tax_year == 2026
