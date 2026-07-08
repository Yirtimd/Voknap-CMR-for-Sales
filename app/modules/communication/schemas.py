from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CommunicationEventCreate(BaseModel):
    channel: str = Field(default="email", min_length=2, max_length=40)
    direction: str = Field(default="inbound", max_length=20)
    external_id: str | None = Field(default=None, max_length=255)
    sender: str | None = Field(default=None, max_length=255)
    recipient: str | None = Field(default=None, max_length=255)
    subject: str = Field(min_length=2, max_length=255)
    body: str | None = None
    occurred_at: datetime | None = None
    company_id: UUID | None = None
    contact_id: UUID | None = None
    deal_id: UUID | None = None
    connector_account_id: UUID | None = None
    metadata: dict = Field(default_factory=dict)


class CommunicationEventLink(BaseModel):
    company_id: UUID | None = None
    contact_id: UUID | None = None
    deal_id: UUID | None = None


class CommunicationIngestRequest(BaseModel):
    channel: str = Field(min_length=2, max_length=40)
    messages: list[CommunicationEventCreate] = Field(default_factory=list)


class CommunicationEventResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    company_id: UUID | None
    contact_id: UUID | None
    deal_id: UUID | None
    activity_id: UUID | None
    connector_account_id: UUID | None
    channel: str
    direction: str
    status: str
    external_id: str | None
    sender: str | None
    recipient: str | None
    occurred_at: datetime
    subject: str
    body: str | None
    ai_summary: str | None
    metadata: dict
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime
