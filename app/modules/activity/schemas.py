from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ActivityCreate(BaseModel):
    company_id: UUID
    contact_id: UUID | None = None
    deal_id: UUID | None = None
    type: str = Field(min_length=2, max_length=40)
    channel: str | None = Field(default=None, max_length=40)
    title: str = Field(min_length=2, max_length=255)
    description: str | None = None
    metadata: dict = Field(default_factory=dict)


class ActivityResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    company_id: UUID
    contact_id: UUID | None
    deal_id: UUID | None
    type: str
    channel: str | None
    title: str
    description: str | None
    created_by: UUID | None
    created_at: datetime
    metadata: dict
