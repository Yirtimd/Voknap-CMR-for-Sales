from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ConnectorDefinitionResponse(BaseModel):
    code: str
    title: str
    description: str
    status: str
    reason: str | None = None


class ConnectorAccountCreate(BaseModel):
    connector_code: str = Field(min_length=2, max_length=80)
    title: str = Field(min_length=2, max_length=255)
    credentials: dict = Field(default_factory=dict)
    settings: dict = Field(default_factory=dict)


class ConnectorAccountResponse(BaseModel):
    id: UUID
    connector_code: str
    title: str
    status: str
    credentials_encrypted: bool = False
    settings: dict
    sync_cursor: str | None = None
    last_sync_at: datetime | None
    created_at: datetime


class CsvImportRequest(BaseModel):
    csv_text: str = Field(min_length=5)


class ConnectorSyncResponse(BaseModel):
    id: UUID
    account_id: UUID
    direction: str
    status: str
    job_type: str = "sync"
    attempt: int = 1
    max_attempts: int = 3
    next_retry_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_count: int
    updated_count: int
    failed_count: int
    message: str | None
    error_code: str | None = None
    error_details: dict = Field(default_factory=dict)
    created_at: datetime


class ConnectorSyncRequest(BaseModel):
    payload: dict = Field(default_factory=dict)
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=255)


class CsvExportResponse(BaseModel):
    filename: str
    csv_text: str


class IntegrationJobResponse(BaseModel):
    id: UUID
    account_id: UUID | None
    job_type: str
    idempotency_key: str
    status: str
    attempt: int
    max_attempts: int
    available_at: datetime
    completed_at: datetime | None
    result: dict
    last_error: str | None
    error_log: list[dict]
    created_at: datetime


class EmailSendRequest(BaseModel):
    recipient: str = Field(min_length=3, max_length=255)
    subject: str = Field(min_length=1, max_length=255)
    body: str = Field(default="", max_length=1_000_000)
    idempotency_key: str = Field(min_length=8, max_length=255)


class CalendarEventCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=100_000)
    starts_at: datetime
    ends_at: datetime
    timezone: str = Field(default="UTC", min_length=1, max_length=80)
    attendees: list[str] = Field(default_factory=list, max_length=100)
    idempotency_key: str = Field(min_length=8, max_length=255)


class OAuthStartResponse(BaseModel):
    authorization_url: str


class WebhookEndpointCreate(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    url: str = Field(min_length=10, max_length=2048)
    event_types: list[str] = Field(min_length=1, max_length=30)


class WebhookEndpointResponse(BaseModel):
    id: UUID
    title: str
    url: str
    event_types: list[str]
    is_active: bool
    signing_secret: str | None = None
    created_at: datetime


class WebhookTestRequest(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=255)


class PublicApiKeyCreate(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    scopes: list[str] = Field(min_length=1, max_length=20)
    expires_at: datetime | None = None


class PublicApiKeyResponse(BaseModel):
    id: UUID
    title: str
    key_prefix: str
    scopes: list[str]
    is_active: bool
    expires_at: datetime | None
    last_used_at: datetime | None
    created_at: datetime
    api_key: str | None = None


class ImportPreviewResponse(BaseModel):
    filename: str
    headers: list[str]
    rows: list[dict]
    suggested_mapping: dict[str, str]
    total_rows: int


class ImportEnqueueResponse(BaseModel):
    job: IntegrationJobResponse
    accepted_rows: int
    validation_errors: list[dict]
