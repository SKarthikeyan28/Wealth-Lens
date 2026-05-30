import logging
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ErrorResponse(BaseModel):
    code: str
    message: str
    detail: Any = None


class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400, detail: Any = None) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.detail = detail


async def app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    logger.warning(
        "app error",
        extra={
            "code": exc.code,
            "status_code": exc.status_code,
            "correlation_id": getattr(request.state, "correlation_id", None),
        },
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(code=exc.code, message=exc.message, detail=exc.detail).model_dump(),
    )
