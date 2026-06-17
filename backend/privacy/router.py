from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.auth.models import User
from backend.common.database import get_db
from backend.common.ratelimit import rate_limit
from backend.privacy.schemas import DeleteAccountRequest
from backend.privacy.service import delete_account, export_data

router = APIRouter(prefix="/account", tags=["account"])


@router.get(
    "/export",
    dependencies=[Depends(rate_limit(limit=5, window=60, scope="account_export"))],
)
async def export_my_data(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    return await export_data(db, user)


@router.delete(
    "",
    status_code=204,
    dependencies=[Depends(rate_limit(limit=5, window=60, scope="account_delete"))],
)
async def delete_my_account(
    body: DeleteAccountRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await delete_account(db, user, body.password)
