from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ProductionOverviewResponse(BaseModel):
    tenant_id: UUID
    counts: dict[str, int]
    plan: dict
    flags: list[dict]


class AuditLogResponse(BaseModel):
    id: UUID
    user_id: UUID | None
    action: str
    entity_type: str | None
    entity_id: str | None
    payload: dict
    created_at: datetime


class FeatureFlagCreate(BaseModel):
    code: str = Field(min_length=2, max_length=120)
    title: str = Field(min_length=2, max_length=255)
    enabled: bool = False


class FeatureFlagUpdate(BaseModel):
    enabled: bool


class FeatureFlagResponse(BaseModel):
    id: UUID
    code: str
    title: str
    enabled: bool
    created_at: datetime


class TenantPlanUpdate(BaseModel):
    plan_code: str = Field(min_length=2, max_length=80)
    users_limit: int = Field(ge=1)
    leads_limit: int = Field(ge=1)
    documents_limit: int = Field(ge=1)
    ai_requests_limit: int = Field(ge=1)


class TenantPlanResponse(BaseModel):
    id: UUID
    plan_code: str
    users_limit: int
    leads_limit: int
    documents_limit: int
    ai_requests_limit: int
    created_at: datetime


class DataExportResponse(BaseModel):
    filename: str
    data: dict

