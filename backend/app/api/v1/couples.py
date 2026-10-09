from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.api.v1.recommendations import get_recommendation_client
from app.core.config import Settings
from app.core.errors import ERROR_RESPONSES, ErrorResponse
from app.services.ai_couple import CoupleRecommendationResponse, recommend_couple
from app.services.ai_recommendation import RecommendationClient
from app.tax.couple import CoupleInput, CoupleOptimizationResult, optimize
from app.tax.rules import get_rules

router = APIRouter(prefix="/couples", tags=["couples"], responses=ERROR_RESPONSES)


@router.post(
    "/optimize",
    response_model=CoupleOptimizationResult,
    summary="맞벌이 부부: 부양가족·의료비·교육비 최적 배분 (모든 조합을 계산 엔진으로 계산)",
)
def optimize_couple(body: CoupleInput) -> CoupleOptimizationResult:
    return optimize(body, get_rules(body.tax_year))


@router.post(
    "/recommendations",
    response_model=CoupleRecommendationResponse,
    responses={
        502: {"model": ErrorResponse, "description": "AI 응답 실패"},
        503: {"model": ErrorResponse, "description": "AI 미설정"},
    },
    summary="맞벌이 부부: 최적 배분에 대한 AI 설명과 추가 팁",
)
def recommend_couple_allocation(
    body: CoupleInput,
    request: Request,
    client: Annotated[RecommendationClient, Depends(get_recommendation_client)],
) -> CoupleRecommendationResponse:
    settings: Settings = request.app.state.settings
    return recommend_couple(body, client, settings.openai_model)
