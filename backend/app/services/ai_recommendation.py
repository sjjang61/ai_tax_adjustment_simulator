"""AI 추천: 추가로 받을 수 있는 공제 항목을 LLM이 제안하고, 효과는 계산 엔진이 산출한다.

설계 원칙
- 세액 계산의 단일 진실 공급원은 계산 엔진이다. LLM은 "무엇을 얼마나 더 하면 좋을지"만 제안하고,
  예상 절세액은 제안을 입력에 반영해 엔진으로 다시 계산한 차이로 구한다.
- 개인 식별 정보 최소화: 부양가족 이름, 교육비 대상자 이름은 LLM에 보내지 않는다.
- OpenAI 호출은 ``RecommendationClient`` 프로토콜 뒤에 두어 테스트에서 대체할 수 있게 한다.
"""

import json
import logging
from typing import Any, Protocol, TypeVar

from openai import OpenAI, OpenAIError
from pydantic import BaseModel

from app.core.errors import AppError
from app.schemas.recommendation import (
    ADJUSTABLE_FIELDS,
    CARD_SHIFT_FIELDS,
    LlmOutput,
    LlmRecommendation,
    Recommendation,
    RecommendationResponse,
)
from app.tax.engine import calculate
from app.tax.inputs import MAX_WON, SimulationInput
from app.tax.result import BreakdownItem, TaxResult
from app.tax.rules import get_rules

logger = logging.getLogger(__name__)

MAX_RECOMMENDATIONS = 5

AI_DISCLAIMER = (
    "AI 추천은 참고용입니다. 예상 절세액은 추천 금액을 입력에 반영해 시뮬레이터가 다시 계산한 값이며, "
    "실제 공제 가능 여부는 요건과 증빙에 따라 달라질 수 있습니다."
)

INSTRUCTIONS = f"""당신은 한국 근로소득 연말정산 절세 도우미입니다.
사용자 메시지의 JSON(계산 결과, 입력 요약, 해당 귀속연도 세법 규칙)만 근거로, 사용자가 추가로 받을 수
있는 공제 항목을 최대 {MAX_RECOMMENDATIONS}개 추천하세요.

규칙:
1. 세액이나 절세액을 직접 계산하거나 숫자로 단정하지 마세요. 절세 효과는 시스템이 따로 계산합니다.
2. 금액을 늘려 효과를 볼 수 있는 항목은 adjustment에 adjustable_fields의 키 하나와 추가 금액(원, 양의 정수)을
   넣으세요. 규칙의 한도에서 현재 입력값을 뺀 잔여 한도를 넘지 않게 하세요.
3. 카드 결제수단(체크카드·전통시장·대중교통·도서공연) 조정은 신용카드 사용분을 옮기는 것으로 계산됩니다.
4. 이미 한도를 채웠거나 요건 미충족(warnings, 무주택·총급여 기준 등)으로 받을 수 없는 항목은 추천하지 마세요.
   요건이 있는 항목은 action에 확인할 요건을 적으세요.
5. 결정세액(determined_tax)이 0원이면 세액공제를 더 받아도 효과가 없으니 그 사실을 summary에 알리세요.
6. 입력 누락이 의심되는 항목(부양가족, 의료비, 교육비 등)은 category를 eligibility_check, adjustment를 null로
   추천할 수 있습니다.
7. 합법적인 방법만 제시하고, 허위 공제나 특정 금융상품 가입 권유는 하지 마세요.
8. 모든 문장은 한국어로 간결하게 작성하세요.
"""


T = TypeVar("T", bound=BaseModel)


class RecommendationClient(Protocol):
    def generate(self, *, instructions: str, payload: str, output_type: type[T]) -> T: ...


class OpenAIRecommendationClient:
    """OpenAI Responses API 구조화 출력으로 추천을 받는다."""

    def __init__(self, *, api_key: str, model: str, timeout: float) -> None:
        self._client = OpenAI(api_key=api_key, timeout=timeout, max_retries=1)
        self.model = model

    def generate(self, *, instructions: str, payload: str, output_type: type[T]) -> T:
        response = self._client.responses.parse(
            model=self.model,
            instructions=instructions,
            input=payload,
            text_format=output_type,
            store=False,
        )
        if response.output_parsed is None:
            raise ValueError("모델 응답을 해석할 수 없습니다.")
        return response.output_parsed


# --------------------------------------------------------------------------- 프롬프트 구성
def _flatten(items: tuple[BreakdownItem, ...], depth: int = 0) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in items:
        if item.amount == 0 and item.applied_amount == 0 and not item.children:
            continue
        out.append(
            {
                "key": item.key,
                "label": item.label,
                "applied": item.applied_amount,
                "unit": item.applied_unit.value,
                "amount": item.amount,
                "limited": item.limited,
                "description": item.description,
            }
        )
        if depth < 2:
            out += _flatten(item.children, depth + 1)
    return out


def anonymize(inp: SimulationInput) -> SimulationInput:
    """부양가족 이름·교육비 대상자 이름을 지운 입력. 계산 결과 숫자에는 영향이 없다."""
    data = inp.model_dump(mode="json")
    for dep in data["dependents"]:
        dep["name"] = ""
    for edu in data["credits"]["education"]:
        edu["label"] = ""
    return SimulationInput.model_validate(data)


def build_payload(inp: SimulationInput) -> str:
    """LLM에 보낼 JSON. 이름 등 식별 정보는 제외한다.

    계산 내역 설명·경고 문구에도 이름이 들어가므로, 익명화한 입력으로 다시 계산한 결과를 보낸다.
    """
    inp = anonymize(inp)
    result = calculate(inp, get_rules(inp.tax_year))
    data = inp.model_dump(mode="json")
    year = inp.tax_year
    data["taxpayer"] = {
        **{k: v for k, v in data["taxpayer"].items() if k != "birth_year"},
        "age": year - inp.taxpayer.birth_year,
    }
    data["dependents"] = [
        {
            "relation": d.relation.value,
            "age": year - d.birth_year,
            "disabled": d.disabled,
            "income_amount": d.income_amount,
            "income_is_salary_only": d.income_is_salary_only,
        }
        for d in inp.dependents
    ]
    data["credits"]["education"] = [
        {"kind": e.kind.value, "amount": e.amount} for e in inp.credits.education
    ]
    payload = {
        "tax_year": year,
        "result": {
            "gross_salary": result.gross_salary,
            "earned_income_amount": result.earned_income_amount,
            "total_income_deduction": result.total_income_deduction,
            "tax_base": result.tax_base,
            "tax_rate": result.tax_rate,
            "calculated_tax": result.calculated_tax,
            "total_tax_credit": result.total_tax_credit,
            "determined_tax": result.determined_tax,
            "total_balance_due": result.total_balance_due,
            "applied_method": result.applied_method.value,
            "method_comparison": [m.model_dump(mode="json") for m in result.method_comparison],
            "income_deductions": _flatten(result.income_deductions),
            "tax_credits": _flatten(result.tax_credits),
            "warnings": [w.message for w in result.warnings],
        },
        "input": data,
        "rules": get_rules(year).model_dump(mode="json"),
        "adjustable_fields": ADJUSTABLE_FIELDS,
    }
    return json.dumps(payload, ensure_ascii=False)


# --------------------------------------------------------------------------- 효과 계산
def apply_adjustment(inp: SimulationInput, field: str, amount: int) -> SimulationInput:
    """입력의 ``field``에 ``amount``를 더한 새 입력을 만든다 (원본 불변).

    카드 결제수단 항목은 신용카드 사용분에서 옮기고, 신용카드가 부족하면 나머지를 추가 사용으로 본다.
    """
    if field not in ADJUSTABLE_FIELDS:
        raise ValueError(f"조정할 수 없는 항목입니다: {field}")
    data = inp.model_dump(mode="json")
    *parents, last = field.split(".")
    node: dict[str, Any] = data
    for part in parents:
        node = node[part]
    node[last] = min(int(node[last]) + amount, MAX_WON)
    if field in CARD_SHIFT_FIELDS:
        card = data["deductions"]["card"]
        card["credit"] = max(card["credit"] - amount, 0)
    return SimulationInput.model_validate(data)


def _to_recommendation(
    rec: LlmRecommendation, inp: SimulationInput, base: TaxResult
) -> Recommendation | None:
    """조정 제안은 엔진으로 효과를 계산한다. 효과가 없거나 잘못된 제안이면 None."""
    adj = rec.adjustment
    if adj is None:
        return Recommendation(
            title=rec.title,
            category=rec.category,
            reason=rec.reason,
            action=rec.action,
            adjustment_field=None,
            adjustment_label=None,
            additional_amount=None,
            estimated_saving=None,
            adjusted_input=None,
        )
    if adj.additional_amount <= 0:
        return None
    try:
        adjusted = apply_adjustment(inp, adj.field, adj.additional_amount)
    except ValueError:
        return None
    new = calculate(adjusted, get_rules(adjusted.tax_year))
    saving = base.total_balance_due - new.total_balance_due
    if saving <= 0:
        return None
    return Recommendation(
        title=rec.title,
        category=rec.category,
        reason=rec.reason,
        action=rec.action,
        adjustment_field=adj.field,
        adjustment_label=ADJUSTABLE_FIELDS[adj.field],
        additional_amount=adj.additional_amount,
        estimated_saving=saving,
        adjusted_input=adjusted,
    )


def recommend(
    inp: SimulationInput, client: RecommendationClient, model_name: str
) -> RecommendationResponse:
    base = calculate(inp, get_rules(inp.tax_year))
    try:
        output = client.generate(
            instructions=INSTRUCTIONS, payload=build_payload(inp), output_type=LlmOutput
        )
    except (OpenAIError, ValueError) as exc:
        logger.warning("AI 추천 생성 실패: %s", type(exc).__name__)
        raise AppError(
            "ai_failed",
            "AI 추천을 생성하지 못했습니다. 잠시 후 다시 시도하세요.",
            status_code=502,
            details={"reason": type(exc).__name__},
        ) from exc

    converted = [_to_recommendation(r, inp, base) for r in output.recommendations]
    kept = [r for r in converted if r is not None][:MAX_RECOMMENDATIONS]
    # 효과를 계산할 수 있는 추천을 절세액 순으로 앞에, 확인 항목은 뒤에 둔다.
    kept.sort(key=lambda r: -(r.estimated_saving or 0))
    return RecommendationResponse(
        model=model_name,
        summary=output.summary,
        base_total_balance_due=base.total_balance_due,
        recommendations=kept,
        discarded_count=len(converted) - len([c for c in converted if c is not None]),
        disclaimer=AI_DISCLAIMER,
    )
