from datetime import datetime

from pydantic import BaseModel


class TgChat(BaseModel):
    id: int


class TgMessage(BaseModel):
    chat: TgChat
    text: str | None = None


class TgUpdate(BaseModel):
    """Minimal subset of a Telegram Update we act on; extra fields are ignored."""

    update_id: int
    message: TgMessage | None = None


class LinkCodeResponse(BaseModel):
    code: str
    expires_at: datetime
