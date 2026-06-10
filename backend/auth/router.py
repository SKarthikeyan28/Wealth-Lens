import uuid

import jwt
from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.models import User
from backend.auth.schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from backend.auth.service import login_user, logout_user, register_user, rotate_refresh
from backend.auth.tokens import decode_access_token
from backend.common.database import get_db
from backend.common.errors import AppError

router = APIRouter(prefix="/auth", tags=["auth"])

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


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    payload: RegisterRequest, db: AsyncSession = Depends(get_db)
) -> UserResponse:
    user = await register_user(db, payload.email, payload.password)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    _, access_token, refresh_token = await login_user(db, payload.email, payload.password)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    payload: RefreshRequest, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    access_token, refresh_token = await rotate_refresh(db, payload.refresh_token)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/logout", status_code=204)
async def logout(
    payload: RefreshRequest, db: AsyncSession = Depends(get_db)
) -> None:
    await logout_user(db, payload.refresh_token)
