"""맞벌이 부부 배분 AI 설명.

최적 배분은 계산 엔진(app.tax.couple.optimize)이 모든 조합을 계산해 정한다. AI는 그 결과를 근거로
"왜 이 배분이 유리한지"를 설명하고, 배분 외에 부부가 챙길 팁을 제안한다. 숫자는 엔진 결과만 사용한다.
"""

import json
import logging

from openai import OpenAIError
from pydantic import BaseModel, ConfigDict, Field

from app.core.errors import AppError
from app.services.ai_recommendation import RecommendationClient, anonymize
from app.tax.couple import CoupleInput, CoupleOptimizationResult, Spouse, medical_category, optimize
from app.tax.rules import get_rules

logger = logging.getLogger(__name__)

AI_COUPLE_DISCLAIMER = (
    "AI 설명은 참고용입니다. 배분별 세액은 시뮬레이터 계산 엔진이 모든 조합을 계산한 결과이며, "
    "실제 공제 가능 여부는 요건과 증빙에 따라 달라질 수 있습니다."
)

COUPLE_INSTRUCTIONS = """당신은 한국 맞벌이 부부의 연말정산 절세 도우미입니다.
사용자 메시지의 JSON에는 부부 각자의 소득·세율 정보, 함께 부양하는 가족(index로 구분), 그리고 시스템이 모든
배분 조합을 계산해 찾은 최적 배분(best)과 현재 배분(baseline), 대안(alternatives)이 들어 있습니다.

규칙:
1. 최적 배분은 이미 시스템이 계산해 확정했습니다. 배분을 바꾸거나 다른 배분을 권하지 마세요.
2. 세액·절세액을 직접 계산하지 말고, 필요하면 JSON에 있는 숫자만 인용하세요.
3. dependent_reasons에는 각 가족(index)이 왜 그 사람에게 가는 것이 유리한지 1~2문장으로 설명하세요.
   근거 예: 한계세율(tax_rate) 차이에 따른 인적공제 효과, 의료비 공제 문턱(총급여의 3%) 차이,
   한도 없는 의료비 여부, 산출세액이 적어 세액공제를 다 못 받는지 여부.
4. tips에는 배분 외에 부부가 챙길 수 있는 합법적인 팁을 최대 3개 적으세요 (예: 신용카드 사용 몰아주기 판단 기준,
   본인 명의 지출 확인). 특정 금융상품 가입 권유는 하지 마세요.
5. 모든 문장은 한국어로 간결하게 작성하세요.
"""


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LlmDependentReason(_Strict):
    index: int = Field(description="shared_dependents의 index")
    reason: str


class LlmCoupleOutput(_Strict):
    summary: str = Field(description="최적 배분 요약 1~2문장")
    dependent_reasons: list[LlmDependentReason]
    tips: list[str]


class CoupleDependentReason(_Strict):
    index: int
    name: str
    recommended_to: Spouse
    reason: str


class CoupleRecommendationResponse(_Strict):
    model: str
    summary: str
    dependent_reasons: list[CoupleDependentReason]
    tips: list[str]
    disclaimer: str


def anonymize_couple(couple: CoupleInput) -> CoupleInput:
    """이름을 모두 지운 부부 입력. 계산·배분 결과는 index 기준으로 원본과 같다."""
    return couple.model_copy(
        update={
            "primary": anonymize(couple.primary),
            "spouse": anonymize(couple.spouse),
            "shared_dependents": tuple(
                d.model_copy(update={"name": ""}) for d in couple.shared_dependents
            ),
        }
    )


def build_couple_payload(couple: CoupleInput, result: CoupleOptimizationResult) -> str:
    """LLM에 보낼 JSON. 이름은 보내지 않고 index로만 구분한다.

    경고·계산 내역 문구에도 이름이 들어가므로 ``anonymize_couple``한 입력과 그 결과를 넘겨야 한다.
    """
    rules = get_rules(couple.tax_year)
    year = couple.tax_year
    p_res, s_res = result.best_primary_result, result.best_spouse_result

    def person(label: str, gross: int, res_rate: str) -> dict[str, object]:
        return {
            "label": label,
            "gross_salary": gross,
            "tax_rate": res_rate,
            "medical_threshold": gross * 3 // 100,
        }

    payload = {
        "tax_year": year,
        "primary": person("본인", couple.primary.gross_salary, p_res.tax_rate),
        "spouse": person("배우자", couple.spouse.gross_salary, s_res.tax_rate),
        "shared_dependents": [
            {
                "index": i,
                "relation": d.relation.value,
                "age": year - d.birth_year,
                "disabled": d.disabled,
                "income_amount": d.income_amount,
                "medical_expense": d.medical_expense,
                "medical_category": medical_category(d, year, rules),
                "education_kind": d.education_kind.value if d.education_kind else None,
                "education_amount": d.education_amount,
                "current": d.assigned_to.value,
                "recommended": result.best.assignment[i].value,
            }
            for i, d in enumerate(couple.shared_dependents)
        ],
        "baseline": result.baseline.model_dump(mode="json"),
        "best": result.best.model_dump(mode="json"),
        "alternatives": [a.model_dump(mode="json") for a in result.alternatives],
        "saving": result.saving,
        "warnings": [w.message for w in (*p_res.warnings, *s_res.warnings)],
    }
    return json.dumps(payload, ensure_ascii=False)


def recommend_couple(
    couple: CoupleInput, client: RecommendationClient, model_name: str
) -> CoupleRecommendationResponse:
    # 이름 없이 최적화해 그 결과를 보낸다 (배분 결과는 index 기준으로 원본과 동일)
    anonymous = anonymize_couple(couple)
    result = optimize(anonymous, get_rules(couple.tax_year))
    try:
        output = client.generate(
            instructions=COUPLE_INSTRUCTIONS,
            payload=build_couple_payload(anonymous, result),
            output_type=LlmCoupleOutput,
        )
    except (OpenAIError, ValueError) as exc:
        logger.warning("맞벌이 AI 설명 생성 실패: %s", type(exc).__name__)
        raise AppError(
            "ai_failed",
            "AI 설명을 생성하지 못했습니다. 잠시 후 다시 시도하세요.",
            status_code=502,
            details={"reason": type(exc).__name__},
        ) from exc

    deps = couple.shared_dependents
    reasons = [
        CoupleDependentReason(
            index=r.index,
            name=deps[r.index].name or f"부양가족 {r.index + 1}",
            recommended_to=result.best.assignment[r.index],
            reason=r.reason,
        )
        for r in output.dependent_reasons
        if 0 <= r.index < len(deps)  # 존재하지 않는 index는 무시
    ]
    return CoupleRecommendationResponse(
        model=model_name,
        summary=output.summary,
        dependent_reasons=reasons,
        tips=output.tips[:3],
        disclaimer=AI_COUPLE_DISCLAIMER,
    )
