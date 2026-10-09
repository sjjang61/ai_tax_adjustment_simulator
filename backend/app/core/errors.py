"""통일된 에러 응답: ``{"code": str, "message": str, "details": object | null}``."""

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.tax.rules import UnsupportedTaxYearError


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details


class NotFoundError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__("not_found", message, status.HTTP_404_NOT_FOUND)


ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {"model": ErrorResponse, "description": "잘못된 요청"},
    404: {"model": ErrorResponse, "description": "리소스 없음"},
    422: {"model": ErrorResponse, "description": "입력 검증 실패"},
}


def _json(status_code: int, code: str, message: str, details: Any = None) -> JSONResponse:
    body = ErrorResponse(code=code, message=message, details=jsonable_encoder(details))
    return JSONResponse(status_code=status_code, content=body.model_dump())


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return _json(exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(UnsupportedTaxYearError)
    async def _unsupported_year(_: Request, exc: UnsupportedTaxYearError) -> JSONResponse:
        from app.tax.rules import SUPPORTED_TAX_YEARS

        return _json(
            status.HTTP_400_BAD_REQUEST,
            "unsupported_tax_year",
            str(exc),
            {"tax_year": exc.tax_year, "supported_years": list(SUPPORTED_TAX_YEARS)},
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {"loc": list(e.get("loc", ())), "msg": e.get("msg", ""), "type": e.get("type", "")}
            for e in exc.errors()
        ]
        return _json(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "validation_error",
            "입력값이 올바르지 않습니다.",
            {"errors": errors},
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = "not_found" if exc.status_code == status.HTTP_404_NOT_FOUND else "http_error"
        return _json(exc.status_code, code, str(exc.detail))
