import logging

from fastapi import FastAPI
from fastapi.routing import APIRouter

from backend.auth.router import router as auth_router
from backend.common.disclaimer import DISCLAIMER
from backend.common.errors import AppError, app_error_handler
from backend.common.logging import configure_logging
from backend.common.middleware import CorrelationIdMiddleware

configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Wealth-Lens",
    description=f"SG Personal Finance Optimizer\n\n> {DISCLAIMER}",
    version="0.1.0",
)

app.add_middleware(CorrelationIdMiddleware)
app.add_exception_handler(AppError, app_error_handler)

api_v1 = APIRouter(prefix="/api/v1")

api_v1.include_router(auth_router)


@api_v1.get("/ping")
def ping() -> dict[str, str]:
    return {"status": "ok", "version": "0.1.0"}


app.include_router(api_v1)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/ready")
async def ready() -> dict[str, str]:
    return {"status": "ready"}
