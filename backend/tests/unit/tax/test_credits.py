"""세액공제 모듈 단위 테스트."""

import pytest

from app.tax.credits.child import child_credit
from app.tax.credits.donation import donation_credits
from app.tax.credits.earned_income import earned_income_credit, earned_income_credit_limit
from app.tax.credits.education import education_credit
from app.tax.credits.insurance import insurance_credit
from app.tax.credits.medical import medical_credit
from app.tax.credits.misc import marriage_credit, monthly_rent_credit, standard_credit
from app.tax.credits.pension_account import pension_account_credit
from app.tax.eligibility import evaluate
from app.tax.inputs import Donations, EducationExpense, EducationKind, MedicalExpenses
from app.tax.rules import get_rules
from tests.factories import make_input

RULES = get_rules(2025)


# ---------------------------------------------------------------- 근로소득세액공제
@pytest.mark.parametrize(
    ("tax", "expected"),
    [
        (0, 0),
        (1_299_999, 714_999),
        (1_300_000, 715_000),
        (1_300_001, 715_000),
        (1_300_004, 715_001),
    ],
)
def test_earned_income_credit_rate_boundary(tax: int, expected: int) -> None:
    assert earned_income_credit(tax, 30_000_000, RULES).amount == expected


@pytest.mark.parametrize(
    ("gross", "limit"),
    [
        (33_000_000, 740_000),
        (33_000_125, 739_999),
        (43_000_000, 660_000),
        (44_000_000, 660_000),  # 652,000 → 하한 660,000
        (70_000_000, 660_000),
        (70_000_002, 659_999),
        (70_320_000, 500_000),
        (120_000_000, 500_000),
        (120_000_002, 499_999),
        (121_000_000, 200_000),
    ],
)
def test_earned_income_credit_limit(gross: int, limit: int) -> None:
    assert earned_income_credit_limit(gross, RULES) == limit


def test_earned_income_credit_limited() -> None:
    item = earned_income_credit(2_000_000, 30_000_000, RULES)
    assert item.amount == 740_000
    assert item.limited


# ---------------------------------------------------------------- 자녀세액공제
def _children(n: int, year: int = 2025, **extra: object) -> int:
    deps = [{"relation": "lineal_descendant", "birth_year": 2010 + i, **extra} for i in range(n)]
    inp = make_input(tax_year=year, taxpayer={"is_married": True}, dependents=deps)
    rules = get_rules(year)
    return child_credit(evaluate(inp, rules), rules).amount


@pytest.mark.parametrize(
    ("n", "expected"), [(0, 0), (1, 250_000), (2, 550_000), (3, 950_000), (4, 1_350_000)]
)
def test_child_credit_counts(n: int, expected: int) -> None:
    assert _children(n) == expected


def test_birth_credit_by_order() -> None:
    inp = make_input(
        taxpayer={"is_married": True},
        dependents=[
            {
                "relation": "lineal_descendant",
                "birth_year": 2025,
                "born_or_adopted_this_year": True,
                "child_order": order,
            }
            for order in (1, 2, 3)
        ],
    )
    item = child_credit(evaluate(inp, RULES), RULES)
    # 0세 자녀는 자녀세액공제(8세 이상) 대상 아님 → 출산·입양분만
    assert item.amount == 300_000 + 500_000 + 700_000


# ---------------------------------------------------------------- 연금계좌
@pytest.mark.parametrize(
    ("savings", "irp", "gross", "expected", "limited"),
    [
        (0, 0, 50_000_000, 0, False),
        (6_000_000, 3_000_000, 55_000_000, 1_350_000, False),
        (6_000_000, 3_000_000, 55_000_001, 1_080_000, False),
        (8_000_000, 0, 50_000_000, 900_000, True),
        (0, 10_000_000, 50_000_000, 1_350_000, True),
        (8_000_000, 2_000_000, 50_000_000, 1_200_000, True),
    ],
)
def test_pension_account(savings: int, irp: int, gross: int, expected: int, limited: bool) -> None:
    item = pension_account_credit(savings, irp, gross, RULES)
    assert (item.amount, item.limited) == (expected, limited)


# ---------------------------------------------------------------- 보험료
@pytest.mark.parametrize(
    ("general", "disabled", "expected", "limited"),
    [
        (0, 0, 0, False),
        (1_000_000, 0, 120_000, False),
        (1_500_000, 0, 120_000, True),
        (0, 1_000_000, 150_000, False),
        (1_000_000, 2_000_000, 270_000, True),
    ],
)
def test_insurance(general: int, disabled: int, expected: int, limited: bool) -> None:
    item = insurance_credit(general, disabled, RULES)
    assert (item.amount, item.limited) == (expected, limited)


# ---------------------------------------------------------------- 의료비 (총급여 5천만 → 3% = 150만)
@pytest.mark.parametrize(
    ("m", "expected"),
    [
        (MedicalExpenses(), 0),
        (MedicalExpenses(general=1_500_000), 0),
        (MedicalExpenses(general=1_500_007), 1),
        (MedicalExpenses(general=3_500_000), 300_000),
        (MedicalExpenses(general=10_000_000), 1_050_000),  # 700만 한도
        (MedicalExpenses(general=1_000_000, specific=2_000_000), 225_000),
        (MedicalExpenses(specific=1_000_000, premature=1_000_000, infertility=1_000_000), 400_000),
        (MedicalExpenses(specific=20_000_000), 2_775_000),  # 특정 의료비는 한도 없음
    ],
)
def test_medical(m: MedicalExpenses, expected: int) -> None:
    assert medical_credit(m, 50_000_000, RULES).amount == expected


def test_medical_general_limit_flag() -> None:
    assert medical_credit(MedicalExpenses(general=10_000_000), 50_000_000, RULES).limited


# ---------------------------------------------------------------- 교육비
@pytest.mark.parametrize(
    ("kind", "amount", "expected", "limited"),
    [
        (EducationKind.SELF, 10_000_000, 1_500_000, False),
        (EducationKind.PRESCHOOL, 3_000_000, 450_000, False),
        (EducationKind.SCHOOL, 3_000_001, 450_000, True),
        (EducationKind.UNIVERSITY, 9_000_000, 1_350_000, False),
        (EducationKind.UNIVERSITY, 10_000_000, 1_350_000, True),
        (EducationKind.DISABLED_SPECIAL, 20_000_000, 3_000_000, False),
    ],
)
def test_education(kind: EducationKind, amount: int, expected: int, limited: bool) -> None:
    item = education_credit([EducationExpense(kind=kind, amount=amount)], RULES)
    assert (item.amount, item.limited) == (expected, limited)


def test_education_per_person() -> None:
    items = [EducationExpense(kind=EducationKind.SCHOOL, amount=3_000_000) for _ in range(2)]
    assert education_credit(items, RULES).amount == 900_000


# ---------------------------------------------------------------- 기부금 (근로소득금액 4천만)
INCOME = 40_000_000


@pytest.mark.parametrize(
    ("d", "expected"),
    [
        (Donations(political=100_000), 90_909),
        (Donations(political=1_000_000), 225_909),
        (Donations(political=31_000_000), 90_909 + 4_485_000 + 250_000),
        (Donations(hometown=100_000), 90_909),
        (Donations(hometown=300_000), 120_909),
        (Donations(hometown_disaster=300_000), 150_909),
        (Donations(hometown=25_000_000), 3_075_909),  # 연간 2천만원 한도
    ],
)
def test_statutory_donations(d: Donations, expected: int) -> None:
    assert donation_credits(d, INCOME, RULES).statutory.amount == expected


@pytest.mark.parametrize(
    ("d", "income", "expected"),
    [
        (Donations(), INCOME, 0),
        (Donations(special=5_000_000), INCOME, 750_000),
        (Donations(special=10_000_000), INCOME, 1_500_000),
        (Donations(special=15_000_000), INCOME, 3_000_000),  # 1천만 초과분 30%
        (Donations(general=20_000_000), INCOME, 2_100_000),  # 한도 1,200만
        (Donations(religious=10_000_000), INCOME, 600_000),  # 한도 400만
        (Donations(general=3_000_000, religious=10_000_000), INCOME, 1_050_000),  # 한도 700만
        (Donations(special=2_000_000), 1_000_000, 150_000),  # 소득금액 한도
    ],
)
def test_special_general_donations(d: Donations, income: int, expected: int) -> None:
    assert donation_credits(d, income, RULES).special.amount == expected


def test_donation_limits_reduce_general_base() -> None:
    # 정치 10만 + 특례 1,990만 → 일반기부금 한도 = (4천만 − 10만 − 1,990만) × 30% = 600만
    d = Donations(political=100_000, special=19_900_000, general=10_000_000)
    item = donation_credits(d, INCOME, RULES).special
    assert item.limited
    assert "한도 6,000,000원" in item.description


# ---------------------------------------------------------------- 월세·표준·결혼
@pytest.mark.parametrize(
    ("rent", "gross", "expected", "limited"),
    [
        (0, 50_000_000, 0, False),
        (12_000_000, 55_000_000, 1_700_000, True),
        (10_000_000, 55_000_001, 1_500_000, False),
    ],
)
def test_monthly_rent(rent: int, gross: int, expected: int, limited: bool) -> None:
    item = monthly_rent_credit(rent, gross, True, RULES)
    assert (item.amount, item.limited) == (expected, limited)


def test_monthly_rent_ineligible() -> None:
    item = monthly_rent_credit(5_000_000, 50_000_000, False, RULES)
    assert item.amount == 0 and item.limited


def test_standard_and_marriage() -> None:
    assert standard_credit(RULES).amount == 130_000
    assert marriage_credit(True, RULES).amount == 500_000
    assert marriage_credit(False, RULES).amount == 0
    assert marriage_credit(True, RULES.model_copy(update={"marriage_credit": None})).amount == 0
