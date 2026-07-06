import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import CurrentTenant, get_current_tenant
from app.modules.templates.models import AppliedTemplate
from app.modules.templates.schemas import (
    AppliedTemplateResponse,
    ApplyTemplateRequest,
    TemplateResponse,
)
from app.modules.templates.service import TemplateService


router = APIRouter()


@router.get("", response_model=list[TemplateResponse])
def list_templates(db: Session = Depends(get_db)) -> list[TemplateResponse]:
    service = TemplateService(db)
    return [
        TemplateResponse(
            code=template.code,
            title=template.title,
            description=template.description,
            pipeline_name=template.pipeline_name,
            stages=template.stages,
            lead_sources=template.lead_sources,
            ai_instruction=template.ai_instruction,
        )
        for template in service.list_templates()
    ]


@router.post("/apply", response_model=AppliedTemplateResponse, status_code=status.HTTP_201_CREATED)
def apply_template(
    payload: ApplyTemplateRequest,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> AppliedTemplateResponse:
    service = TemplateService(db)
    try:
        applied = service.apply_template(
            tenant_id=tenant.id,
            template_code=payload.template_code,
            include_pipeline=payload.include_pipeline,
            include_knowledge=payload.include_knowledge,
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    return _applied_response(applied)


@router.get("/applied", response_model=list[AppliedTemplateResponse])
def list_applied(
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> list[AppliedTemplateResponse]:
    service = TemplateService(db)
    return [_applied_response(applied) for applied in service.list_applied(tenant.id)]


def _applied_response(applied: AppliedTemplate) -> AppliedTemplateResponse:
    return AppliedTemplateResponse(
        id=applied.id,
        template_code=applied.template_code,
        template_title=applied.template_title,
        status=applied.status,
        result=json.loads(applied.result_json),
        created_at=applied.created_at,
    )

