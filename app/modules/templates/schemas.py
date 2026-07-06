from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class TemplateResponse(BaseModel):
    code: str
    title: str
    description: str
    pipeline_name: str
    stages: list[str]
    lead_sources: list[str]
    ai_instruction: str


class ApplyTemplateRequest(BaseModel):
    template_code: str = Field(min_length=2, max_length=80)
    include_pipeline: bool = True
    include_knowledge: bool = True


class AppliedTemplateResponse(BaseModel):
    id: UUID
    template_code: str
    template_title: str
    status: str
    result: dict
    created_at: datetime

