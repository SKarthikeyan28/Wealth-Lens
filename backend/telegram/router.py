import logging

from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.auth.models import User
from backend.common.database import get_db
from backend.telegram.client import TelegramUnavailable, get_telegram_client
from backend.telegram.schemas import LinkCodeResponse, TgUpdate
from backend.telegram.security import verify_webhook_secret
from backend.telegram.service import create_link_code, handle_update

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telegram", tags=["telegram"])


@router.post("/webhook")
async def telegram_webhook(
    update: TgUpdate,
    x_telegram_secret: str | None = Header(default=None, alias="X-Telegram-Bot-Api-Secret-Token"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    verify_webhook_secret(x_telegram_secret)  # 403 on mismatch — the auth boundary
    try:
        await handle_update(db, get_telegram_client(), update)
    except TelegramUnavailable:
        # We acted (any DB write committed); we just couldn't reply. Don't 5xx,
        # or Telegram will retry and we'd double-process.
        logger.warning("telegram send failed", extra={"update_id": update.update_id})
    return {"ok": True}


@router.post("/link-code", response_model=LinkCodeResponse)
async def get_link_code(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LinkCodeResponse:
    code, expires_at = await create_link_code(db, user.id)
    return LinkCodeResponse(code=code, expires_at=expires_at)
