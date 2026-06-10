import hashlib
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.models import RefreshToken, User
from backend.auth.security import check_password_strength, hash_password, verify_password
from backend.auth.tokens import (
    create_access_token,
    generate_refresh_token,
    refresh_token_expiry,
)
from backend.common.errors import AppError


def _hash_token(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


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


async def login_user(
    db: AsyncSession, email: str, password: str
) -> tuple[User, str, str]:
    normalised = email.lower().strip()
    user = await db.scalar(select(User).where(User.email == normalised))
    if user is None or not verify_password(password, user.password_hash):
        raise AppError("INVALID_CREDENTIALS", "Invalid email or password.", 401)

    refresh_value = generate_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            family_id=uuid.uuid4(),
            token_hash=_hash_token(refresh_value),
            expires_at=refresh_token_expiry(),
        )
    )
    await db.commit()

    return user, create_access_token(user.id), refresh_value


async def rotate_refresh(db: AsyncSession, token_value: str) -> tuple[str, str]:
    rt = await db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == _hash_token(token_value))
    )

    if rt is None or rt.revoked:
        raise AppError("INVALID_TOKEN", "Refresh token is invalid.", 401)

    if rt.expires_at < datetime.now(timezone.utc):
        raise AppError("INVALID_TOKEN", "Refresh token has expired.", 401)

    if rt.consumed:
        # Reuse detected — revoke the entire family to lock out all sessions
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == rt.family_id)
            .values(revoked=True)
        )
        await db.commit()
        raise AppError("SECURITY_EVENT", "Token reuse detected. All sessions revoked.", 401)

    rt.consumed = True
    new_refresh_value = generate_refresh_token()
    db.add(
        RefreshToken(
            user_id=rt.user_id,
            family_id=rt.family_id,
            token_hash=_hash_token(new_refresh_value),
            expires_at=refresh_token_expiry(),
        )
    )
    await db.commit()

    return create_access_token(rt.user_id), new_refresh_value


async def logout_user(db: AsyncSession, token_value: str) -> None:
    rt = await db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == _hash_token(token_value))
    )
    if rt is not None and not rt.consumed and not rt.revoked:
        rt.consumed = True
        await db.commit()
