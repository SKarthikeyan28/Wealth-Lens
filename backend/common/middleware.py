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


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Defence-in-depth response headers. This is a JSON API (it serves no HTML/JS),
    so the CSP is maximally restrictive; the Next.js frontend sets its own UI CSP."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        # HSTS is honoured only over HTTPS; browsers ignore it on plain HTTP (dev).
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        return response
