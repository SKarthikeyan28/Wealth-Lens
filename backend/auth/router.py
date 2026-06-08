from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.schemas import RegisterRequest, UserResponse
from backend.auth.service import register_user
from backend.common.database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    payload: RegisterRequest, db: AsyncSession = Depends(get_db)
) -> UserResponse:
    user = await register_user(db, payload.email, payload.password)
    return UserResponse.model_validate(user)
