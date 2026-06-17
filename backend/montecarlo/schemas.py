from pydantic import BaseModel


class YearBandOut(BaseModel):
    year: int
    p10: float
    p25: float
    p50: float
    p75: float
    p90: float


class ProjectionResponse(BaseModel):
    probability: float
    goal_amount: float
    years: int
    initial_wealth: float
    annual_contribution: float
    mean_return: float
    volatility: float
    n_sims: int
    seed: int
    bands: list[YearBandOut]
