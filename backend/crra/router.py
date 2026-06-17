from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.auth.models import User
from backend.common.database import get_db
from backend.common.errors import AppError
from backend.common.ratelimit import rate_limit
from backend.crra.elicitation import ladder
from backend.crra.schemas import (
    AllocationResponse,
    AllocationSliceOut,
    AssessmentRequest,
    FrontierPointOut,
    FrontierResponse,
    LadderQuestionOut,
    RiskProfileResponse,
)
from backend.crra.service import (
    frontier_analysis,
    get_risk_profile,
    optimal_allocation,
    submit_questionnaire,
)

router = APIRouter(prefix="/risk", tags=["risk"])


@router.get("/ladder", response_model=list[LadderQuestionOut])
async def get_ladder(
    user: User = Depends(get_current_user),
) -> list[LadderQuestionOut]:
    return [
        LadderQuestionOut(
            gamble_high=q.gamble_high,
            gamble_low=q.gamble_low,
            sure_amount=q.sure_amount,
            gamma_cut=q.gamma_cut,
        )
        for q in ladder()
    ]


@router.post("/assessment", response_model=RiskProfileResponse, status_code=201)
async def submit_assessment(
    payload: AssessmentRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RiskProfileResponse:
    rp = await submit_questionnaire(db, user.id, payload.answers)
    return RiskProfileResponse.model_validate(rp)


@router.get("/profile", response_model=RiskProfileResponse)
async def get_profile(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RiskProfileResponse:
    rp = await get_risk_profile(db, user.id)
    if rp is None:
        raise AppError(
            "RISK_PROFILE_NOT_FOUND",
            "No risk profile; complete the questionnaire.",
            404,
        )
    return RiskProfileResponse.model_validate(rp)


@router.get(
    "/allocation",
    response_model=AllocationResponse,
    dependencies=[Depends(rate_limit(limit=10, window=60, scope="crra_alloc"))],
)
async def get_allocation(
    start: date | None = None,
    end: date | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AllocationResponse:
    on_end = end or date.today()
    on_start = start or on_end.replace(year=on_end.year - 5)  # 5y default lookback
    result = await optimal_allocation(db, user.id, start=on_start, end=on_end)
    return AllocationResponse(
        crra_gamma=result.crra_gamma,
        expected_return=result.expected_return,
        volatility=result.volatility,
        slices=[
            AllocationSliceOut(ticker=s.ticker, weight=s.weight) for s in result.slices
        ],
    )


@router.get(
    "/frontier",
    response_model=FrontierResponse,
    dependencies=[Depends(rate_limit(limit=10, window=60, scope="crra_frontier"))],
)
async def get_frontier(
    start: date | None = None,
    end: date | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FrontierResponse:
    on_end = end or date.today()
    on_start = start or on_end.replace(year=on_end.year - 5)  # 5y default lookback
    fa = await frontier_analysis(db, user.id, start=on_start, end=on_end)
    return FrontierResponse(
        frontier=[
            FrontierPointOut(expected_return=p.expected_return, volatility=p.volatility)
            for p in fa.frontier
        ],
        user_return=fa.user_return,
        user_volatility=fa.user_volatility,
        optimal_return=fa.optimal_return,
        optimal_volatility=fa.optimal_volatility,
        crra_gamma=fa.crra_gamma,
    )
