import logging

from fastapi import FastAPI

from backend.common.logging import configure_logging
from backend.common.middleware import CorrelationIdMiddleware

configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Wealth-Lens",
    description="SG Personal Finance Optimizer — educational analysis tool, not financial advice.",
    version="0.1.0",
)

app.add_middleware(CorrelationIdMiddleware)


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok", "version": "0.1.0"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/ready")
async def ready() -> dict[str, str]:
    # Phase 0.3+: check DB + Redis connectivity here once sessions are wired
    return {"status": "ready"}
