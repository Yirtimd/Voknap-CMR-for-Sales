from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentCreate(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    text: str = Field(min_length=20)
    source_type: str = Field(default="text", max_length=40)


class DocumentResponse(BaseModel):
    id: UUID
    title: str
    source_type: str
    status: str
    created_at: datetime
    chunks_count: int = 0


class SearchRequest(BaseModel):
    query: str = Field(min_length=2)
    limit: int = Field(default=6, ge=1, le=20)


class SearchResultResponse(BaseModel):
    chunk_id: UUID
    document_id: UUID
    document_title: str
    text: str
    score: float
    chunk_index: int


class AskRequest(BaseModel):
    question: str = Field(min_length=2)
    limit: int = Field(default=6, ge=1, le=12)


class CitationResponse(BaseModel):
    chunk_id: UUID
    document_id: UUID
    document_title: str
    chunk_index: int
    text: str
    score: float


class AskResponse(BaseModel):
    answer: str
    citations: list[CitationResponse]

