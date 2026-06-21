from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: str
    filename: str
    uploaded_at: str


class AskRequest(BaseModel):
    session_id: str
    question: str


class AskResponse(BaseModel):
    answer: str
