from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.auth.models import User
from backend.common.database import get_db
from backend.montecarlo.schemas import ProjectionResponse, YearBandOut
from backend.montecarlo.service import project_goal

router = APIRouter(prefix="/projection", tags=["projection"])


@router.get("/goal", response_model=ProjectionResponse)
async def get_goal_projection(
    goal_amount: float,
    years: int,
    initial_wealth: float,
    annual_contribution: float,
    n_sims: int = 10000,
    seed: int = 42,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectionResponse:
    result = await project_goal(
        db,
        user.id,
        goal_amount=goal_amount,
        years=years,
        initial_wealth=initial_wealth,
        annual_contribution=annual_contribution,
        n_sims=n_sims,
        seed=seed,
    )
    return ProjectionResponse(
        probability=result.probability,
        goal_amount=result.goal_amount,
        years=result.years,
        initial_wealth=result.initial_wealth,
        annual_contribution=result.annual_contribution,
        mean_return=result.mean_return,
        volatility=result.volatility,
        n_sims=result.n_sims,
        seed=result.seed,
        bands=[
            YearBandOut(
                year=b.year,
                p10=b.p10,
                p25=b.p25,
                p50=b.p50,
                p75=b.p75,
                p90=b.p90,
            )
            for b in result.bands
        ],
    )
