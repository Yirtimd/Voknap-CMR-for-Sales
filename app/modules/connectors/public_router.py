from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.connectors.api_keys import PublicApiPrincipal, get_public_api_principal
from app.modules.connectors.jobs import publish_webhook_event
from app.modules.sales.models import Lead
from app.modules.sales.schemas import LeadCreate, LeadResponse


router = APIRouter()


@router.get("/leads", response_model=list[LeadResponse])
def list_leads(
    principal: Annotated[PublicApiPrincipal, Depends(get_public_api_principal)],
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[Lead]:
    principal.require("leads:read")
    return (
        db.query(Lead)
        .filter(Lead.tenant_id == principal.tenant_id)
        .order_by(Lead.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.post("/leads", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
def create_lead(
    payload: LeadCreate,
    principal: Annotated[PublicApiPrincipal, Depends(get_public_api_principal)],
    db: Session = Depends(get_db),
) -> Lead:
    principal.require("leads:write")
    lead = Lead(tenant_id=principal.tenant_id, **payload.model_dump())
    db.add(lead)
    db.commit()
    db.refresh(lead)
    publish_webhook_event(
        db,
        tenant_id=principal.tenant_id,
        event_type="lead.created",
        data={"id": str(lead.id), "title": lead.title, "source": lead.source},
        actor_id=None,
    )
    return lead
