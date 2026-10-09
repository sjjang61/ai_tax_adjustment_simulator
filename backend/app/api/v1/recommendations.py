from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.core.config import Settings
from app.core.errors import ERROR_RESPONSES, AppError, ErrorResponse
from app.schemas.recommendation import RecommendationResponse
from app.services.ai_recommendation import (
    OpenAIRecommendationClient,
    RecommendationClient,
    recommend,
)
from app.tax.inputs import SimulationInput

router = APIRouter(
    prefix="/recommendations",
    tags=["recommendations"],
    responses={
        **ERROR_RESPONSES,
        502: {"model": ErrorResponse, "description": "AI 응답 실패"},
        503: {"model": ErrorResponse, "description": "AI 미설정"},
    },
)


def get_recommendation_client(request: Request) -> RecommendationClient:
    settings: Settings = request.app.state.settings
    api_key = settings.openai_api_key.get_secret_value()
    if not api_key:
        raise AppError(
            "ai_unavailable",
            "AI 추천을 사용하려면 서버에 OPENAI_API_KEY를 설정해야 합니다.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return OpenAIRecommendationClient(
        api_key=api_key, model=settings.openai_model, timeout=settings.openai_timeout_seconds
    )


@router.post(
    "",
    response_model=RecommendationResponse,
    summary="AI 추천: 추가로 받을 수 있는 공제 항목 (절세액은 계산 엔진이 산출)",
)
def create_recommendations(
    body: SimulationInput,
    request: Request,
    client: Annotated[RecommendationClient, Depends(get_recommendation_client)],
) -> RecommendationResponse:
    settings: Settings = request.app.state.settings
    return recommend(body, client, settings.openai_model)
