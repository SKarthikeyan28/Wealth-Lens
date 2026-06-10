import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    requires_2fa: bool
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "bearer"
    pre_auth_token: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TotpEnrolResponse(BaseModel):
    provisioning_uri: str
    secret: str


class TotpConfirmRequest(BaseModel):
    totp_code: str


class TotpConfirmResponse(BaseModel):
    recovery_codes: list[str]


class TotpVerifyRequest(BaseModel):
    pre_auth_token: str
    totp_code: str


class TotpRecoverRequest(BaseModel):
    pre_auth_token: str
    recovery_code: str


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    created_at: datetime

    model_config = {"from_attributes": True}
