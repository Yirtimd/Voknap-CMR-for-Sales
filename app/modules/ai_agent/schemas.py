from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AgentChatRequest(BaseModel):
    message: str = Field(min_length=2)


class AgentActionResponse(BaseModel):
    id: UUID
    action_type: str
    status: str
    payload: dict
    result: dict | None = None
    created_at: datetime
    confirmed_at: datetime | None = None


class AgentChatResponse(BaseModel):
    answer: str
    actions: list[AgentActionResponse] = Field(default_factory=list)
    sources: list[dict] = Field(default_factory=list)


class AgentHistoryMessage(BaseModel):
    id: UUID
    role: str
    content: str
    created_at: datetime

