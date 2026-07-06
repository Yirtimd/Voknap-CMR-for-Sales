from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ConnectorDefinitionResponse(BaseModel):
    code: str
    title: str
    description: str
    status: str


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
    settings: dict
    last_sync_at: datetime | None
    created_at: datetime


class CsvImportRequest(BaseModel):
    csv_text: str = Field(min_length=5)


class ConnectorSyncResponse(BaseModel):
    id: UUID
    account_id: UUID
    direction: str
    status: str
    created_count: int
    updated_count: int
    failed_count: int
    message: str | None
    created_at: datetime

class CsvExportResponse(BaseModel):
    filename: str
    csv_text: str

