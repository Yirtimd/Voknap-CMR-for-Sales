from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, model_validator


class ContactCreate(BaseModel):
    company_id: UUID
    name: str = Field(min_length=2, max_length=255)
    phone: str | None = Field(default=None, max_length=80)
    email: EmailStr | None = None
    company_name: str | None = Field(default=None, max_length=255)


class ContactResponse(BaseModel):
    id: UUID
    company_id: UUID
    name: str
    phone: str | None
    email: str | None
    company_name: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CompanyCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    website: str | None = Field(default=None, max_length=255)
    industry: str | None = Field(default=None, max_length=120)
    description: str | None = None


class CompanyResponse(BaseModel):
    id: UUID
    name: str
    website: str | None
    industry: str | None
    description: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CompanyWorkspaceResponse(BaseModel):
    company: CompanyResponse
    overview: dict
    contacts: list[ContactResponse]
    deals: list["DealResponse"]
    tasks: list["TaskResponse"]
    activities: list[dict]
    ai_summary: str
    ai_insights: list[str]


class LeadCreate(BaseModel):
    company_id: UUID
    title: str = Field(min_length=2, max_length=255)
    source: str | None = Field(default=None, max_length=80)
    contact_id: UUID | None = None


class LeadResponse(BaseModel):
    id: UUID
    company_id: UUID
    title: str
    source: str | None
    status: str
    contact_id: UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PipelineCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    stages: list[str] = Field(default_factory=lambda: ["Новый", "В работе", "КП", "Сделка"])


class PipelineStageResponse(BaseModel):
    id: UUID
    name: str
    sort_order: int

    model_config = {"from_attributes": True}


class PipelineResponse(BaseModel):
    id: UUID
    name: str
    stages: list[PipelineStageResponse]
    created_at: datetime

    model_config = {"from_attributes": True}


class DealCreate(BaseModel):
    company_id: UUID
    title: str = Field(min_length=2, max_length=255)
    stage_id: UUID
    lead_id: UUID | None = None
    amount: float | None = Field(default=None, ge=0)


class DealMoveRequest(BaseModel):
    stage_id: UUID


class DealResponse(BaseModel):
    id: UUID
    company_id: UUID
    title: str
    amount: float | None
    status: str
    lead_id: UUID | None
    stage_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class TaskCreate(BaseModel):
    company_id: UUID
    title: str = Field(min_length=2, max_length=255)
    description: str | None = None
    deal_id: UUID | None = None
    due_at: datetime | None = None


class TaskDoneRequest(BaseModel):
    is_done: bool = True


class TaskResponse(BaseModel):
    id: UUID
    company_id: UUID
    title: str
    description: str | None
    deal_id: UUID | None
    due_at: datetime | None
    done_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class NoteCreate(BaseModel):
    company_id: UUID
    text: str = Field(min_length=1)
    lead_id: UUID | None = None
    deal_id: UUID | None = None

    @model_validator(mode="after")
    def validate_target(self) -> "NoteCreate":
        if self.lead_id is None and self.deal_id is None:
            raise ValueError("lead_id or deal_id required")
        return self


class NoteResponse(BaseModel):
    id: UUID
    company_id: UUID
    text: str
    lead_id: UUID | None
    deal_id: UUID | None
    author_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}
