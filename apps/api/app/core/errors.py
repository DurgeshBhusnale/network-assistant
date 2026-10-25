"""Error codes and the `{"error": {"code", "message"}}` envelope for every error response."""

import logging
from enum import StrEnum

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class ErrorCode(StrEnum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNAUTHENTICATED = "UNAUTHENTICATED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
    CONFLICT = "CONFLICT"
    RATE_LIMITED = "RATE_LIMITED"
    HTTP_ERROR = "HTTP_ERROR"
    PRIVACY_NOTICE_REQUIRED = "PRIVACY_NOTICE_REQUIRED"
    PACK_NOT_AVAILABLE = "PACK_NOT_AVAILABLE"
    GOAL_ALREADY_ACTIVE = "GOAL_ALREADY_ACTIVE"
    INTERNAL_ERROR = "INTERNAL_ERROR"


_STATUS_CODES = {
    401: ErrorCode.UNAUTHENTICATED,
    403: ErrorCode.FORBIDDEN,
    404: ErrorCode.NOT_FOUND,
    405: ErrorCode.METHOD_NOT_ALLOWED,
    409: ErrorCode.CONFLICT,
    429: ErrorCode.RATE_LIMITED,
}


class ErrorDetail(BaseModel):
    code: ErrorCode
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class AppError(Exception):
    """Raise from routes and services; rendered as the error envelope."""

    def __init__(self, code: ErrorCode, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def error_response(status_code: int, code: ErrorCode, message: str) -> JSONResponse:
    body = ErrorResponse(error=ErrorDetail(code=code, message=message))
    return JSONResponse(status_code=status_code, content=body.model_dump(mode="json"))


async def _app_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    return error_response(exc.status_code, exc.code, exc.message)


async def _http_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    code = _STATUS_CODES.get(exc.status_code, ErrorCode.HTTP_ERROR)
    return error_response(exc.status_code, code, str(exc.detail))


async def _validation_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    # Field locations only; input values may contain PII and are never echoed back.
    fields = sorted({".".join(str(p) for p in err["loc"]) for err in exc.errors()})
    return error_response(422, ErrorCode.VALIDATION_ERROR, "Invalid request: " + ", ".join(fields))


async def _unhandled_error(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_error", extra={"error_type": type(exc).__name__})
    return error_response(500, ErrorCode.INTERNAL_ERROR, "Something went wrong. Please try again.")


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error)
    app.add_exception_handler(StarletteHTTPException, _http_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(Exception, _unhandled_error)
