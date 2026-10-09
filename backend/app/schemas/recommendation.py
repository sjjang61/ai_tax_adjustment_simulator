"""AI 추천 스키마.

- ``Llm*``: OpenAI 구조화 출력(JSON Schema strict)으로 받는 모델 응답 형식
- ``Recommendation*``: API 응답. 예상 절세액은 LLM이 아니라 계산 엔진이 산출한다.
"""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.tax.inputs import SimulationInput

# AI가 금액 조정을 제안할 수 있는 입력 항목 (경로 → 표시 이름)
ADJUSTABLE_FIELDS: dict[str, str] = {
    "credits.pension_savings": "연금저축 납입액",
    "credits.irp": "퇴직연금(IRP) 납입액",
    "credits.insurance_general": "보장성보험료",
    "credits.donations.hometown": "고향사랑기부금",
    "credits.donations.special": "특례기부금",
    "credits.donations.general": "일반기부금",
    "credits.monthly_rent": "월세 지급액",
    "deductions.housing_subscription": "주택청약종합저축 납입액",
    "deductions.card.debit_cash": "체크카드·현금영수증 사용액",
    "deductions.card.traditional_market": "전통시장 사용액",
    "deductions.card.public_transport": "대중교통 사용액",
    "deductions.card.culture": "도서·공연 등 사용액",
    "deductions.venture_fund": "벤처투자조합 출자액",
}

AdjustableField = Literal[
    "credits.pension_savings",
    "credits.irp",
    "credits.insurance_general",
    "credits.donations.hometown",
    "credits.donations.special",
    "credits.donations.general",
    "credits.monthly_rent",
    "deductions.housing_subscription",
    "deductions.card.debit_cash",
    "deductions.card.traditional_market",
    "deductions.card.public_transport",
    "deductions.card.culture",
    "deductions.venture_fund",
]

# 신용카드 외 결제수단 항목은 "추가 지출"이 아니라 신용카드 사용분을 옮기는 것으로 계산한다.
CARD_SHIFT_FIELDS = frozenset(
    {
        "deductions.card.debit_cash",
        "deductions.card.traditional_market",
        "deductions.card.public_transport",
        "deductions.card.culture",
    }
)


class RecommendationCategory(StrEnum):
    INCOME_DEDUCTION = "income_deduction"  # 소득공제
    TAX_CREDIT = "tax_credit"  # 세액공제
    ELIGIBILITY_CHECK = "eligibility_check"  # 누락·요건 확인
    OTHER = "other"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LlmAdjustment(_Strict):
    field: AdjustableField = Field(description="adjustable_fields의 키")
    additional_amount: int = Field(description="현재 입력값에 더할 금액(원, 양의 정수)")


class LlmRecommendation(_Strict):
    title: str = Field(description="추천 제목 (30자 이내)")
    category: RecommendationCategory
    reason: str = Field(description="추천 이유 (현재 상태와 한도·요건 근거)")
    action: str = Field(description="사용자가 할 일과 확인할 요건")
    adjustment: LlmAdjustment | None = Field(description="금액 조정 제안, 없으면 null")


class LlmOutput(_Strict):
    summary: str = Field(description="전체 요약 1~2문장")
    recommendations: list[LlmRecommendation]


class Recommendation(_Strict):
    title: str
    category: RecommendationCategory
    reason: str
    action: str
    adjustment_field: str | None
    adjustment_label: str | None
    additional_amount: int | None
    estimated_saving: int | None = Field(
        description="계산 엔진이 산출한 예상 절세액(지방소득세 포함, 원). 금액 조정이 없으면 null"
    )
    adjusted_input: SimulationInput | None = Field(
        description="추천을 반영한 입력 (프론트의 '적용' 버튼용)"
    )


class RecommendationResponse(_Strict):
    model: str
    summary: str
    base_total_balance_due: int
    recommendations: list[Recommendation]
    discarded_count: int = Field(description="절세 효과가 없어 제외한 AI 제안 수")
    disclaimer: str
