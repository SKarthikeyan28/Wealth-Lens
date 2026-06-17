from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.auth.models import User
from backend.chatbot.schemas import ChatRequest, ChatResponse
from backend.chatbot.service import answer
from backend.common.database import get_db
from backend.common.ratelimit import rate_limit

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post(
    "",
    response_model=ChatResponse,
    dependencies=[Depends(rate_limit(limit=20, window=60, scope="chat"))],
)
async def post_chat(
    body: ChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    on = body.as_of or date.today()
    text = await answer(db, user, body.question, body.base.upper(), on)
    return ChatResponse(answer=text)
