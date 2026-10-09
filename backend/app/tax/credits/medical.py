"""의료비 세액공제 (소득세법 제59조의4 제2항).

총급여 3% 미달액은 일반 의료비에서 먼저 차감하고, 부족하면 특정 의료비 → 미숙아·선천성이상아 →
난임시술비 순서로 차감한다 (국세청 의료비 세액공제 계산 순서).
"""

from decimal import Decimal

from app.tax.inputs import MedicalExpenses
from app.tax.money import apply_rate, format_percent
from app.tax.result import BreakdownItem
from app.tax.rules.base import TaxRules


def medical_credit(m: MedicalExpenses, gross_salary: int, rules: TaxRules) -> BreakdownItem:
    r = rules.medical_credit
    threshold = apply_rate(gross_salary, r.threshold_rate)  # 총급여 × 3%, 원 미만 절사

    # 1) 일반 의료비: 3% 초과분, 연 700만원 한도
    general_excess = m.general - threshold
    if general_excess >= 0:
        general_target = min(general_excess, r.general_limit)
        shortfall = 0
    else:
        general_target = 0
        shortfall = -general_excess

    # 2) 나머지 항목: 남은 미달액을 순서대로 차감
    targets: list[tuple[str, str, int, Decimal]] = []
    for key, label, amount, rate in (
        ("specific", "본인·65세 이상·장애인·6세 이하 등", m.specific, r.specific_rate),
        ("premature", "미숙아·선천성이상아", m.premature, r.premature_rate),
        ("infertility", "난임시술비", m.infertility, r.infertility_rate),
    ):
        used = min(amount, shortfall)
        shortfall -= used
        targets.append((key, label, amount - used, rate))

    children = [
        BreakdownItem(
            key="medical_credit.general",
            label="그 밖의 부양가족",
            applied_amount=m.general,
            amount=apply_rate(general_target, r.general_rate),
            limited=general_excess > r.general_limit,
            description=(
                f"(지출액 − 총급여 {format_percent(r.threshold_rate)} {threshold:,}원), 한도 {r.general_limit:,}원 × "
                f"{format_percent(r.general_rate)}"
            ),
        )
    ]
    source = {"specific": m.specific, "premature": m.premature, "infertility": m.infertility}
    for key, label, target, rate in targets:
        children.append(
            BreakdownItem(
                key=f"medical_credit.{key}",
                label=label,
                applied_amount=source[key],
                amount=apply_rate(target, rate),
                description=f"공제대상 {target:,}원 × {format_percent(rate)} (한도 없음)",
            )
        )
    total_spent = m.general + m.specific + m.premature + m.infertility
    return BreakdownItem(
        key="medical_credit",
        label="의료비",
        applied_amount=total_spent,
        amount=sum(x.amount for x in children),
        limited=any(x.limited for x in children),
        description=(
            f"총급여의 {format_percent(r.threshold_rate)}({threshold:,}원) 초과 지출분부터 공제"
            if total_spent
            else ""
        ),
        children=tuple(children),
    )
