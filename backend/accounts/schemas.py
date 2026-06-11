import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from backend.accounts.models import AccountType


class AccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    account_type: AccountType
    currency: str = Field(default="SGD", min_length=3, max_length=3)
    cash_balance: Decimal = Field(default=Decimal("0"), ge=0)

    @field_validator("currency")
    @classmethod
    def _upper(cls, v: str) -> str:
        return v.upper()


class AccountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    cash_balance: Decimal | None = Field(default=None, ge=0)

    @field_validator("currency")
    @classmethod
    def _upper(cls, v: str | None) -> str | None:
        return v.upper() if v is not None else v


class AccountResponse(BaseModel):
    id: uuid.UUID
    name: str
    account_type: AccountType
    currency: str
    cash_balance: Decimal
    created_at: datetime

    model_config = {"from_attributes": True}
