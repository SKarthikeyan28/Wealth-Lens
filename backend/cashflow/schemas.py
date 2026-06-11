import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from backend.cashflow.models import IncomeSource


class IncomeCreate(BaseModel):
    source_type: IncomeSource = IncomeSource.SALARY
    amount: Decimal = Field(ge=0)
    currency: str = Field(default="SGD", min_length=3, max_length=3)
    received_on: date
    note: str | None = None

    @field_validator("currency")
    @classmethod
    def _upper(cls, v: str) -> str:
        return v.upper()


class IncomeUpdate(BaseModel):
    source_type: IncomeSource | None = None
    amount: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    received_on: date | None = None
    note: str | None = None

    @field_validator("currency")
    @classmethod
    def _upper(cls, v: str | None) -> str | None:
        return v.upper() if v is not None else v


class IncomeResponse(BaseModel):
    id: uuid.UUID
    source_type: IncomeSource
    amount: Decimal
    currency: str
    received_on: date
    note: str | None

    model_config = {"from_attributes": True}


class ExpenseCreate(BaseModel):
    category: str = Field(min_length=1, max_length=80)
    amount: Decimal = Field(ge=0)
    currency: str = Field(default="SGD", min_length=3, max_length=3)
    spent_on: date
    note: str | None = None

    @field_validator("currency")
    @classmethod
    def _upper(cls, v: str) -> str:
        return v.upper()


class ExpenseUpdate(BaseModel):
    category: str | None = Field(default=None, min_length=1, max_length=80)
    amount: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    spent_on: date | None = None
    note: str | None = None

    @field_validator("currency")
    @classmethod
    def _upper(cls, v: str | None) -> str | None:
        return v.upper() if v is not None else v


class ExpenseResponse(BaseModel):
    id: uuid.UUID
    category: str
    amount: Decimal
    currency: str
    spent_on: date
    note: str | None

    model_config = {"from_attributes": True}
