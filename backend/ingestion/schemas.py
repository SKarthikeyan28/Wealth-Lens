import uuid
from datetime import datetime

from pydantic import BaseModel


class ImportReceiptResponse(BaseModel):
    id: uuid.UUID
    source: str
    filename: str
    total_rows: int
    inserted: int
    skipped_duplicates: int
    failed: int
    errors: list[dict[str, object]]
    created_at: datetime

    model_config = {"from_attributes": True}
