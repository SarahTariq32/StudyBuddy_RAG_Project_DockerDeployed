from pydantic import BaseModel, Field  # type: ignore
from typing import Optional


class DocumentOut(BaseModel):
    id: str
    filename: str
    status: str
    uploaded_at: Optional[str] = None


class DocumentRenameRequest(BaseModel):
    filename: Optional[str] = Field(default=None, min_length=1, max_length=255)
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)


class AskRequest(BaseModel):
    question: str = Field(min_length=1)


class AskResponse(BaseModel):
    answer: str
