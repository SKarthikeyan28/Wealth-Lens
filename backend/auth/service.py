import hashlib
import secrets
import uuid
from datetime import datetime, timezone

import pyotp
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.encryption import decrypt, encrypt
from backend.auth.models import RecoveryCode, RefreshToken, User
from backend.auth.security import check_password_strength, hash_password, verify_password
from backend.auth.tokens import (
    create_access_token,
    create_preauth_token,
    decode_preauth_token,
    generate_refresh_token,
    refresh_token_expiry,
)
from backend.common.errors import AppError

_RECOVERY_CODE_COUNT = 8


def _hash_token(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _normalize_recovery_code(code: str) -> str:
    return code.upper().replace("-", "").replace(" ", "")


def _generate_recovery_code() -> str:
    return f"{secrets.token_hex(3).upper()}-{secrets.token_hex(3).upper()}"


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


async def login_user(db: AsyncSession, email: str, password: str) -> dict[str, object]:
    normalised = email.lower().strip()
    user = await db.scalar(select(User).where(User.email == normalised))
    if user is None or not verify_password(password, user.password_hash):
        raise AppError("INVALID_CREDENTIALS", "Invalid email or password.", 401)

    if user.totp_enabled:
        return {"requires_2fa": True, "pre_auth_token": create_preauth_token(user.id)}

    access_token, refresh_token = await _issue_tokens(db, user.id)
    return {"requires_2fa": False, "access_token": access_token, "refresh_token": refresh_token}


async def _issue_tokens(db: AsyncSession, user_id: uuid.UUID) -> tuple[str, str]:
    refresh_value = generate_refresh_token()
    db.add(
        RefreshToken(
            user_id=user_id,
            family_id=uuid.uuid4(),
            token_hash=_hash_token(refresh_value),
            expires_at=refresh_token_expiry(),
        )
    )
    await db.commit()
    return create_access_token(user_id), refresh_value


async def _resolve_preauth(db: AsyncSession, pre_auth_token: str) -> User:
    try:
        payload = decode_preauth_token(pre_auth_token)
    except Exception:
        raise AppError("INVALID_TOKEN", "Invalid or expired pre-auth token.", 401)
    user = await db.scalar(select(User).where(User.id == uuid.UUID(str(payload["sub"]))))
    if user is None:
        raise AppError("INVALID_TOKEN", "User not found.", 401)
    return user


async def rotate_refresh(db: AsyncSession, token_value: str) -> tuple[str, str]:
    rt = await db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == _hash_token(token_value))
    )

    if rt is None or rt.revoked:
        raise AppError("INVALID_TOKEN", "Refresh token is invalid.", 401)

    if rt.expires_at < datetime.now(timezone.utc):
        raise AppError("INVALID_TOKEN", "Refresh token has expired.", 401)

    if rt.consumed:
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


async def enroll_totp(db: AsyncSession, user: User) -> tuple[str, str]:
    secret = pyotp.random_base32()
    uri = pyotp.TOTP(secret).provisioning_uri(name=user.email, issuer_name="Wealth-Lens")
    user.totp_secret = encrypt(secret)
    user.totp_enabled = False
    await db.commit()
    return uri, secret


async def confirm_totp(db: AsyncSession, user: User, totp_code: str) -> list[str]:
    if not user.totp_secret:
        raise AppError("TOTP_NOT_ENROLLED", "TOTP enrollment not started.", 400)
    if not pyotp.TOTP(decrypt(user.totp_secret)).verify(totp_code, valid_window=1):
        raise AppError("INVALID_TOTP", "Invalid TOTP code.", 401)

    await db.execute(delete(RecoveryCode).where(RecoveryCode.user_id == user.id))
    codes = [_generate_recovery_code() for _ in range(_RECOVERY_CODE_COUNT)]
    for code in codes:
        db.add(
            RecoveryCode(
                user_id=user.id,
                code_hash=_hash_token(_normalize_recovery_code(code)),
            )
        )
    user.totp_enabled = True
    await db.commit()
    return codes


async def verify_totp_login(
    db: AsyncSession, pre_auth_token: str, totp_code: str
) -> tuple[str, str]:
    user = await _resolve_preauth(db, pre_auth_token)
    if not user.totp_enabled or not user.totp_secret:
        raise AppError("TOTP_NOT_ENROLLED", "2FA not configured.", 400)
    if not pyotp.TOTP(decrypt(user.totp_secret)).verify(totp_code, valid_window=1):
        raise AppError("INVALID_TOTP", "Invalid TOTP code.", 401)
    return await _issue_tokens(db, user.id)


async def verify_recovery_login(
    db: AsyncSession, pre_auth_token: str, recovery_code: str
) -> tuple[str, str]:
    user = await _resolve_preauth(db, pre_auth_token)
    code_hash = _hash_token(_normalize_recovery_code(recovery_code))
    rc = await db.scalar(
        select(RecoveryCode).where(
            RecoveryCode.user_id == user.id,
            RecoveryCode.code_hash == code_hash,
            RecoveryCode.used.is_(False),
        )
    )
    if rc is None:
        raise AppError("INVALID_RECOVERY_CODE", "Invalid or already used recovery code.", 401)
    rc.used = True
    await db.commit()
    return await _issue_tokens(db, user.id)
