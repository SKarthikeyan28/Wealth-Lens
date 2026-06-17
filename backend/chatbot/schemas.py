from datetime import date

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    base: str = "SGD"
    as_of: date | None = None


class ChatResponse(BaseModel):
    answer: str
