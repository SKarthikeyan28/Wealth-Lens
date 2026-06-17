from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class LadderQuestionOut(BaseModel):
    gamble_high: float
    gamble_low: float
    sure_amount: float
    gamma_cut: float


class AssessmentRequest(BaseModel):
    answers: list[bool]


class RiskProfileResponse(BaseModel):
    crra_gamma: Decimal
    crra_gamma_low: Decimal
    crra_gamma_high: Decimal
    assessed_at: datetime

    model_config = {"from_attributes": True}


class AllocationSliceOut(BaseModel):
    ticker: str
    weight: float


class AllocationResponse(BaseModel):
    crra_gamma: Decimal
    expected_return: float
    volatility: float
    slices: list[AllocationSliceOut]


class FrontierPointOut(BaseModel):
    expected_return: float
    volatility: float


class FrontierResponse(BaseModel):
    frontier: list[FrontierPointOut]
    user_return: float | None
    user_volatility: float | None
    optimal_return: float | None
    optimal_volatility: float | None
    crra_gamma: Decimal | None
