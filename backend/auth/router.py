from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.auth.models import User
from backend.auth.schemas import (
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    TotpConfirmRequest,
    TotpConfirmResponse,
    TotpEnrolResponse,
    TotpRecoverRequest,
    TotpVerifyRequest,
    UserResponse,
)
from backend.auth.service import (
    confirm_totp,
    enroll_totp,
    login_user,
    logout_user,
    register_user,
    rotate_refresh,
    verify_recovery_login,
    verify_totp_login,
)
from backend.common.database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    payload: RegisterRequest, db: AsyncSession = Depends(get_db)
) -> UserResponse:
    user = await register_user(db, payload.email, payload.password)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest, db: AsyncSession = Depends(get_db)
) -> LoginResponse:
    result = await login_user(db, payload.email, payload.password)
    return LoginResponse.model_validate(result)


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


@router.post("/totp/enroll", response_model=TotpEnrolResponse)
async def totp_enroll(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TotpEnrolResponse:
    uri, secret = await enroll_totp(db, user)
    return TotpEnrolResponse(provisioning_uri=uri, secret=secret)


@router.post("/totp/confirm", response_model=TotpConfirmResponse)
async def totp_confirm(
    payload: TotpConfirmRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TotpConfirmResponse:
    codes = await confirm_totp(db, user, payload.totp_code)
    return TotpConfirmResponse(recovery_codes=codes)


@router.post("/totp/verify", response_model=TokenResponse)
async def totp_verify(
    payload: TotpVerifyRequest, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    access_token, refresh_token = await verify_totp_login(
        db, payload.pre_auth_token, payload.totp_code
    )
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/totp/recover", response_model=TokenResponse)
async def totp_recover(
    payload: TotpRecoverRequest, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    access_token, refresh_token = await verify_recovery_login(
        db, payload.pre_auth_token, payload.recovery_code
    )
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)
