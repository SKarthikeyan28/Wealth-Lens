from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.models import User
from backend.auth.security import check_password_strength, hash_password
from backend.common.errors import AppError


async def register_user(db: AsyncSession, email: str, password: str) -> User:
    check_password_strength(password)

    normalised = email.lower().strip()
    existing = await db.scalar(select(User).where(User.email == normalised))
    if existing is not None:
        raise AppError("EMAIL_TAKEN", "An account with this email already exists.", 409)

    user = User(email=normalised, password_hash=hash_password(password))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
