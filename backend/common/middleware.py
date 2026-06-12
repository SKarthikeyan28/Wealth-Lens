import logging
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        request.state.correlation_id = correlation_id

        logger.info(
            "request started",
            extra={
                "correlation_id": correlation_id,
                "path": request.url.path,
                "method": request.method,
            },
        )

        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id

        logger.info(
            "request finished",
            extra={"correlation_id": correlation_id, "status_code": response.status_code},
        )
        return response
