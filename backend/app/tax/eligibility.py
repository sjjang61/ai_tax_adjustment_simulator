"""공제 대상 요건 판정.

계산과 분리된 검증 함수로, 요건 위반은 예외가 아닌 경고(CalcWarning)로 반환한다.
요건을 충족하지 못한 항목은 계산에서 제외되며, 경고로 그 이유를 알린다.
"""

from dataclasses import dataclass

from app.tax.deductions.earned_income import earned_income_deduction
from app.tax.inputs import Dependent, Relation, SimulationInput
from app.tax.result import CalcWarning, WarningLevel
from app.tax.rules.base import TaxRules

_CHILD_RELATIONS = frozenset({Relation.LINEAL_DESCENDANT, Relation.FOSTER_CHILD})

_RELATION_LABELS = {
    Relation.SPOUSE: "배우자",
    Relation.LINEAL_ASCENDANT: "직계존속",
    Relation.LINEAL_DESCENDANT: "직계비속",
    Relation.SIBLING: "형제자매",
    Relation.FOSTER_CHILD: "위탁아동",
}


@dataclass(frozen=True)
class PersonStatus:
    """기본공제 대상자(본인 포함) 한 명의 판정 결과."""

    label: str
    relation: Relation | None  # None = 본인
    dependent_index: int | None  # 입력 dependents의 위치 (본인은 None)
    age: int
    basic_eligible: bool
    elderly: bool
    disabled: bool
    child_credit_eligible: bool
    birth_order: int | None  # 해당 연도 출생·입양 시 순서


@dataclass(frozen=True)
class Eligibility:
    persons: tuple[PersonStatus, ...]
    female_deduction: bool
    single_parent_deduction: bool
    housing_subscription_eligible: bool
    rent_loan_eligible: bool
    monthly_rent_eligible: bool
    warnings: tuple[CalcWarning, ...]

    @property
    def basic_persons(self) -> tuple[PersonStatus, ...]:
        return tuple(p for p in self.persons if p.basic_eligible)

    @property
    def eligible_child_count(self) -> int:
        """기본공제 대상 자녀(직계비속·위탁아동) 수 — 연령 무관."""
        return sum(1 for p in self.basic_persons if p.relation in _CHILD_RELATIONS)

    @property
    def child_credit_count(self) -> int:
        return sum(1 for p in self.basic_persons if p.child_credit_eligible)


def age_in_tax_year(birth_year: int, tax_year: int) -> int:
    """세법상 연령: 해당 과세기간 중 도래하는 나이 (소득세법 제50조 제1항, 연 단위 판정)."""
    return tax_year - birth_year


def _dependent_label(index: int, dep: Dependent) -> str:
    return dep.name or f"{_RELATION_LABELS[dep.relation]} {index + 1}"


def _age_requirement_met(dep: Dependent, age: int, rules: TaxRules) -> bool:
    p = rules.personal
    if dep.disabled or dep.relation is Relation.SPOUSE:
        return True  # 장애인·배우자는 나이 요건 없음 (소득세법 제50조 제1항 단서)
    if dep.relation is Relation.LINEAL_ASCENDANT:
        return age >= p.ascendant_min_age
    if dep.relation in _CHILD_RELATIONS:
        return age <= p.descendant_max_age
    return age <= p.sibling_max_age or age >= p.sibling_min_age


def _income_requirement_met(dep: Dependent, rules: TaxRules) -> bool:
    p = rules.personal
    limit = p.dependent_salary_only_limit if dep.income_is_salary_only else p.dependent_income_limit
    return dep.income_amount <= limit


def evaluate(inp: SimulationInput, rules: TaxRules, extra_income: int = 0) -> Eligibility:
    """extra_income: 근로소득 외 종합소득금액 (사업·기타소득, 결손이면 음수)."""
    warnings: list[CalcWarning] = []
    year = inp.tax_year
    p = rules.personal
    gross = inp.gross_salary

    if not rules.verified:
        warnings.append(
            CalcWarning(
                code="rules_unverified",
                message=f"{year}년 귀속 세법 규칙은 공식 자료로 검증되지 않아 결과가 부정확할 수 있습니다.",
            )
        )

    tp = inp.taxpayer
    tp_age = age_in_tax_year(tp.birth_year, year)
    persons: list[PersonStatus] = [
        PersonStatus(
            label="본인",
            relation=None,
            dependent_index=None,
            age=tp_age,
            basic_eligible=True,
            elderly=tp_age >= p.elderly_min_age,
            disabled=tp.disabled,
            child_credit_eligible=False,
            birth_order=None,
        )
    ]

    spouse_count = 0
    for i, dep in enumerate(inp.dependents):
        label = _dependent_label(i, dep)
        field = f"dependents[{i}]"
        age = age_in_tax_year(dep.birth_year, year)
        if age < 0:
            warnings.append(
                CalcWarning(
                    code="dependent_not_born",
                    message=f"{label}: 출생연도가 귀속연도 이후라 공제 대상에서 제외했습니다.",
                    field=f"{field}.birth_year",
                )
            )
            continue
        eligible = True
        if dep.relation is Relation.SPOUSE:
            spouse_count += 1
            if spouse_count > 1:
                eligible = False
                warnings.append(
                    CalcWarning(
                        code="duplicate_spouse",
                        message=f"{label}: 배우자는 1명만 공제할 수 있어 제외했습니다.",
                        field=field,
                    )
                )
        if eligible and not _age_requirement_met(dep, age, rules):
            eligible = False
            warnings.append(
                CalcWarning(
                    code="dependent_age_requirement",
                    message=f"{label}: 나이 요건({age}세)을 충족하지 않아 기본공제에서 제외했습니다.",
                    field=f"{field}.birth_year",
                )
            )
        if eligible and not _income_requirement_met(dep, rules):
            eligible = False
            limit = (
                p.dependent_salary_only_limit
                if dep.income_is_salary_only
                else p.dependent_income_limit
            )
            warnings.append(
                CalcWarning(
                    code="dependent_income_requirement",
                    message=f"{label}: 소득 요건({limit:,}원 이하)을 초과해 기본공제에서 제외했습니다.",
                    field=f"{field}.income_amount",
                )
            )

        birth_order: int | None = None
        if eligible and dep.born_or_adopted_this_year:
            if dep.relation not in _CHILD_RELATIONS:
                warnings.append(
                    CalcWarning(
                        code="birth_relation_mismatch",
                        message=f"{label}: 출산·입양 세액공제는 자녀에게만 적용됩니다.",
                        field=f"{field}.born_or_adopted_this_year",
                    )
                )
            else:
                if dep.child_order is None:
                    warnings.append(
                        CalcWarning(
                            code="birth_order_missing",
                            message=f"{label}: 출생·입양 순서가 없어 첫째로 간주했습니다.",
                            field=f"{field}.child_order",
                        )
                    )
                birth_order = dep.child_order or 1

        persons.append(
            PersonStatus(
                label=label,
                relation=dep.relation,
                dependent_index=i,
                age=age,
                basic_eligible=eligible,
                elderly=eligible and age >= p.elderly_min_age,
                disabled=eligible and dep.disabled,
                child_credit_eligible=(
                    eligible
                    and dep.relation in _CHILD_RELATIONS
                    and age >= rules.child_credit.min_age
                ),
                birth_order=birth_order,
            )
        )

    # 추가공제: 부녀자·한부모 (소득세법 제51조 제1항 제3호·제4호)
    # 부녀자공제 소득 요건은 종합소득금액 기준 (제51조 제1항 제3호)
    earned_income_amount_estimate = max(_earned_income_amount(gross, rules) + extra_income, 0)
    has_basic_dependents = any(x.basic_eligible for x in persons[1:])
    has_basic_children = any(
        x.basic_eligible and x.relation in _CHILD_RELATIONS for x in persons[1:]
    )
    # 배우자를 부양가족으로 등록했으면 배우자가 있는 것으로 본다.
    has_spouse = tp.is_married or any(d.relation is Relation.SPOUSE for d in inp.dependents)
    single_parent = (not has_spouse) and has_basic_children
    female = (
        tp.is_female
        and earned_income_amount_estimate <= p.female_earned_income_limit
        and (has_spouse or (tp.is_household_head and has_basic_dependents))
    )
    if female and single_parent:
        female = False
        warnings.append(
            CalcWarning(
                code="female_and_single_parent",
                message="부녀자공제와 한부모공제가 중복되어 한부모공제만 적용했습니다.",
                level=WarningLevel.INFO,
            )
        )

    d = inp.deductions
    subscription_ok = True
    if d.housing_subscription > 0:
        if not tp.is_homeless:
            subscription_ok = False
            warnings.append(
                CalcWarning(
                    code="housing_subscription_not_homeless",
                    message="주택청약종합저축 공제는 무주택 세대주(배우자)만 받을 수 있어 제외했습니다.",
                    field="deductions.housing_subscription",
                )
            )
        elif gross > rules.housing.subscription_gross_salary_limit:
            subscription_ok = False
            warnings.append(
                CalcWarning(
                    code="housing_subscription_salary_limit",
                    message=(
                        "주택청약종합저축 공제는 총급여 "
                        f"{rules.housing.subscription_gross_salary_limit:,}원 이하만 받을 수 있어 "
                        "제외했습니다."
                    ),
                    field="deductions.housing_subscription",
                )
            )

    rent_loan_ok = True
    if d.housing_rent_loan_repayment > 0 and not tp.is_homeless:
        rent_loan_ok = False
        warnings.append(
            CalcWarning(
                code="rent_loan_not_homeless",
                message="주택임차차입금 공제는 무주택 세대주만 받을 수 있어 제외했습니다.",
                field="deductions.housing_rent_loan_repayment",
            )
        )
    if d.long_term_mortgage_interest > 0 and d.mortgage_type is None:
        warnings.append(
            CalcWarning(
                code="mortgage_type_missing",
                message="장기주택저당차입금 한도 유형을 선택하지 않아 이자상환액 공제를 제외했습니다.",
                field="deductions.mortgage_type",
            )
        )

    rent_ok = True
    if inp.credits.monthly_rent > 0:
        if not tp.is_homeless:
            rent_ok = False
            warnings.append(
                CalcWarning(
                    code="monthly_rent_not_homeless",
                    message="월세 세액공제는 무주택 세대주(세대원)만 받을 수 있어 제외했습니다.",
                    field="credits.monthly_rent",
                )
            )
        elif gross > rules.rent_credit.gross_salary_limit:
            rent_ok = False
            warnings.append(
                CalcWarning(
                    code="monthly_rent_salary_limit",
                    message=(
                        f"월세 세액공제는 총급여 {rules.rent_credit.gross_salary_limit:,}원 "
                        "이하만 받을 수 있어 제외했습니다."
                    ),
                    field="credits.monthly_rent",
                )
            )

    card = d.card
    if (card.culture or card.sports_facility) and gross > rules.card.culture_gross_salary_limit:
        warnings.append(
            CalcWarning(
                code="card_culture_salary_limit",
                message=(
                    "총급여 7천만원 초과자는 도서·공연·체육시설 사용분에 별도 공제율이 적용되지 않아 "
                    "신용카드 공제율로 계산했습니다."
                ),
                level=WarningLevel.INFO,
                field="deductions.card.culture",
            )
        )

    fund = rules.national_growth_fund
    if d.national_growth_fund > 0:
        if fund is None:
            warnings.append(
                CalcWarning(
                    code="national_growth_fund_unavailable",
                    message=f"{year}년 귀속에는 국민성장펀드 소득공제가 없어 제외했습니다.",
                    field="deductions.national_growth_fund",
                )
            )
        else:
            warnings.append(
                CalcWarning(
                    code="national_growth_fund_holding_period",
                    message=(
                        f"국민성장펀드 소득공제는 전용계좌로 {fund.min_holding_years}년 이상 보유해야 하며, "
                        "그 전에 환매하면 감면세액이 추징될 수 있습니다."
                    ),
                    level=WarningLevel.INFO,
                    field="deductions.national_growth_fund",
                )
            )

    if tp.marriage_registered_this_year:
        if rules.marriage_credit is None:
            warnings.append(
                CalcWarning(
                    code="marriage_credit_unavailable",
                    message=f"{year}년 귀속에는 결혼세액공제가 없습니다.",
                    field="taxpayer.marriage_registered_this_year",
                )
            )
        else:
            warnings.append(
                CalcWarning(
                    code="marriage_credit_once",
                    message="결혼세액공제는 생애 1회만 적용됩니다. 이전에 받은 적이 없는지 확인하세요.",
                    level=WarningLevel.INFO,
                    field="taxpayer.marriage_registered_this_year",
                )
            )

    return Eligibility(
        persons=tuple(persons),
        female_deduction=female,
        single_parent_deduction=single_parent,
        housing_subscription_eligible=subscription_ok,
        rent_loan_eligible=rent_loan_ok,
        monthly_rent_eligible=rent_ok,
        warnings=tuple(warnings),
    )


def _earned_income_amount(gross: int, rules: TaxRules) -> int:
    """근로소득금액 (부녀자공제 소득 요건 판정용)."""
    return gross - earned_income_deduction(gross, rules).amount
