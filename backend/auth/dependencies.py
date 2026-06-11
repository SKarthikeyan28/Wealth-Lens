import uuid

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.models import User
from backend.auth.tokens import decode_access_token
from backend.common.database import get_db
from backend.common.errors import AppError

_bearer = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.PyJWTError:
        raise AppError("INVALID_TOKEN", "Invalid or expired access token.", 401)
    user = await db.scalar(
        select(User).where(User.id == uuid.UUID(str(payload["sub"])))
    )
    if user is None:
        raise AppError("INVALID_TOKEN", "User not found.", 401)
    return user
