import uuid

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.auth.models import User
from backend.common.database import get_db
from backend.ingestion.schemas import ImportReceiptResponse
from backend.ingestion.service import get_import_receipt, import_expenses_csv

router = APIRouter(prefix="/imports", tags=["imports"])


@router.post("/expenses", response_model=ImportReceiptResponse, status_code=201)
async def import_expenses(
    file: UploadFile,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ImportReceiptResponse:
    content = await file.read()
    receipt = await import_expenses_csv(db, user.id, file.filename or "upload.csv", content)
    return ImportReceiptResponse.model_validate(receipt)


@router.get("/{receipt_id}", response_model=ImportReceiptResponse)
async def get_receipt(
    receipt_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ImportReceiptResponse:
    receipt = await get_import_receipt(db, user.id, receipt_id)
    return ImportReceiptResponse.model_validate(receipt)
