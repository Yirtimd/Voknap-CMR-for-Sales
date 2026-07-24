from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.modules.sales.schemas import DealResponse, LeadResponse


class VersionedRequest(BaseModel):
    version: int = Field(ge=1)


class ContactUpdate(VersionedRequest):
    company_id: UUID | None = None
    name: str | None = Field(default=None, min_length=2, max_length=255)
    phone: str | None = Field(default=None, max_length=80)
    email: EmailStr | None = None
    company_name: str | None = Field(default=None, max_length=255)
    role: str | None = Field(default=None, max_length=120)
    owner_id: UUID | None = None


class LeadUpdate(VersionedRequest):
    company_id: UUID | None = None
    contact_id: UUID | None = None
    title: str | None = Field(default=None, min_length=2, max_length=255)
    source: str | None = Field(default=None, max_length=80)
    status: str | None = Field(default=None, max_length=80)
    owner_id: UUID | None = None


class DealUpdate(VersionedRequest):
    company_id: UUID | None = None
    lead_id: UUID | None = None
    stage_id: UUID | None = None
    title: str | None = Field(default=None, min_length=2, max_length=255)
    amount: float | None = Field(default=None, ge=0)
    discount_percent: float | None = Field(default=None, ge=0, le=100)
    status: str | None = Field(default=None, max_length=40)
    probability: int | None = Field(default=None, ge=0, le=100)
    expected_close_date: datetime | None = None
    expected_next_event: str | None = Field(default=None, max_length=255)
    next_step: str | None = Field(default=None, max_length=255)
    risk_level: str | None = Field(default=None, max_length=40)
    forecast_category: str | None = Field(default=None, max_length=40)
    owner_id: UUID | None = None


class TaskUpdate(VersionedRequest):
    company_id: UUID | None = None
    deal_id: UUID | None = None
    title: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = None
    status: str | None = Field(default=None, max_length=40)
    priority: str | None = Field(default=None, max_length=40)
    due_at: datetime | None = None
    assigned_to_id: UUID | None = None


class NoteUpdate(VersionedRequest):
    text: str | None = Field(default=None, min_length=1)


class ArchiveRequest(VersionedRequest):
    is_archived: bool = True


class RestoreRequest(VersionedRequest):
    pass


class ReassignRequest(VersionedRequest):
    owner_id: UUID


class LeadQualificationRequest(VersionedRequest):
    qualified: bool = True
    reason: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def require_disqualification_reason(self):
        if not self.qualified and not self.reason:
            raise ValueError("Disqualification reason is required")
        return self


class LeadConversionRequest(VersionedRequest):
    stage_id: UUID
    title: str | None = Field(default=None, min_length=2, max_length=255)
    amount: float | None = Field(default=None, ge=0)
    owner_id: UUID | None = None


class LeadConversionResponse(BaseModel):
    lead: LeadResponse
    deal: DealResponse


class EntityVersion(BaseModel):
    id: UUID
    version: int = Field(ge=1)


class MergeRequest(BaseModel):
    target_version: int = Field(ge=1)
    sources: list[EntityVersion] = Field(min_length=1, max_length=100)


BulkAction = Literal["archive", "unarchive", "delete", "restore", "reassign"]


class BulkActionRequest(BaseModel):
    action: BulkAction
    items: list[EntityVersion] = Field(min_length=1, max_length=200)
    owner_id: UUID | None = None

    @model_validator(mode="after")
    def require_owner_for_reassignment(self):
        if self.action == "reassign" and self.owner_id is None:
            raise ValueError("owner_id is required for reassignment")
        return self


class BulkActionResponse(BaseModel):
    affected: int
    action: BulkAction


class MergeResponse(BaseModel):
    target_id: UUID
    merged_ids: list[UUID]
    version: int


class DuplicateScanRequest(BaseModel):
    entity_type: Literal["contacts", "leads", "deals"]
    minimum_score: int = Field(default=80, ge=50, le=100)
    limit: int = Field(default=200, ge=1, le=500)


class DuplicateCandidateResponse(BaseModel):
    id: UUID
    entity_type: str
    record_a_id: UUID
    record_b_id: UUID
    score: int
    matched_fields: list[str]
    status: str
    version: int
    detected_at: datetime
    resolved_at: datetime | None


class DuplicateDismissRequest(BaseModel):
    version: int = Field(ge=1)
    comment: str = Field(min_length=1, max_length=1000)


class FieldChangeResponse(BaseModel):
    id: UUID
    entity_type: str
    entity_id: UUID
    field_name: str
    old_value: object | None
    new_value: object | None
    changed_by_id: UUID
    entity_version: int
    created_at: datetime
