"""FastAPI 앱 생성, 라우터 등록, CORS."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import (
    businesses,
    couples,
    global_income,
    import_export,
    recommendations,
    rules,
    simulations,
)
from app.core.config import Settings, get_settings
from app.core.errors import register_error_handlers
from app.db import build_engine, build_session_factory, init_db

API_PREFIX = "/api/v1"

# 로컬 개발: Vite가 사용 중인 포트를 피해 5174 등으로 뜨는 경우가 있어 localhost의 모든 포트를 허용한다.
LOCAL_ORIGIN_REGEX = r"https?://(localhost|127\.0\.0\.1)(:\d+)?"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    engine = build_engine(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        init_db(engine)
        yield
        engine.dispose()

    app = FastAPI(
        title="연말정산 시뮬레이터 API",
        version="0.1.0",
        description="근로소득 연말정산 예상 결정세액·환급액 계산 (참고용 시뮬레이션)",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.session_factory = build_session_factory(engine)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        # local에서만 localhost 임의 포트 허용. production은 CORS_ORIGINS 목록만 허용한다.
        allow_origin_regex=LOCAL_ORIGIN_REGEX if settings.app_env == "local" else None,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition"],
    )
    register_error_handlers(app)

    api = APIRouter(prefix=API_PREFIX)
    # import/export를 먼저 등록해 /simulations/import 가 /{simulation_id} 보다 우선 매칭되게 한다.
    api.include_router(import_export.router)
    api.include_router(simulations.router)
    api.include_router(rules.router)
    api.include_router(recommendations.router)
    api.include_router(couples.router)
    api.include_router(global_income.router)
    api.include_router(businesses.router)
    app.include_router(api)

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
