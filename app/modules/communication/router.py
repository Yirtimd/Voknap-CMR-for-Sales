import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import CurrentTenant, get_current_tenant
from app.modules.communication.models import CommunicationEvent
from app.modules.communication.schemas import (
    CommunicationEventCreate,
    CommunicationEventLink,
    CommunicationEventResponse,
    CommunicationIngestRequest,
)
from app.modules.communication.service import CommunicationService


router = APIRouter()


@router.get("/events", response_model=list[CommunicationEventResponse])
def list_events(
    channel: str | None = None,
    status: str | None = None,
    company_id: UUID | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> list[CommunicationEventResponse]:
    service = CommunicationService(db)
    return [
        _event_response(event)
        for event in service.list(
            tenant_id=tenant.id,
            channel=channel,
            status=status,
            company_id=company_id,
            limit=limit,
        )
    ]


@router.post("/events", response_model=CommunicationEventResponse, status_code=status.HTTP_201_CREATED)
def create_event(
    payload: CommunicationEventCreate,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> CommunicationEventResponse:
    event = CommunicationService(db).create(tenant_id=tenant.id, created_by=tenant.user_id, payload=payload)
    return _event_response(event)


@router.post("/ingest", response_model=list[CommunicationEventResponse], status_code=status.HTTP_201_CREATED)
def ingest_events(
    payload: CommunicationIngestRequest,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> list[CommunicationEventResponse]:
    service = CommunicationService(db)
    events = service.ingest(
        tenant_id=tenant.id,
        created_by=tenant.user_id,
        channel=payload.channel,
        messages=payload.messages,
    )
    return [_event_response(event) for event in events]


@router.patch("/events/{event_id}/link", response_model=CommunicationEventResponse)
def link_event(
    event_id: UUID,
    payload: CommunicationEventLink,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> CommunicationEventResponse:
    event = CommunicationService(db).link(tenant_id=tenant.id, event_id=event_id, payload=payload)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Communication event not found")
    return _event_response(event)


@router.post("/events/{event_id}/activity", response_model=CommunicationEventResponse)
def create_activity_from_event(
    event_id: UUID,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> CommunicationEventResponse:
    event = CommunicationService(db).create_activity(tenant_id=tenant.id, event_id=event_id, created_by=tenant.user_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Communication event not found")
    if event.company_id is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Link event to company before activity creation")
    return _event_response(event)


@router.post("/events/{event_id}/summary", response_model=CommunicationEventResponse)
def refresh_event_summary(
    event_id: UUID,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> CommunicationEventResponse:
    event = CommunicationService(db).refresh_summary(tenant_id=tenant.id, event_id=event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Communication event not found")
    return _event_response(event)


def _event_response(event: CommunicationEvent) -> CommunicationEventResponse:
    return CommunicationEventResponse(
        id=event.id,
        tenant_id=event.tenant_id,
        company_id=event.company_id,
        contact_id=event.contact_id,
        deal_id=event.deal_id,
        activity_id=event.activity_id,
        connector_account_id=event.connector_account_id,
        channel=event.channel,
        direction=event.direction,
        status=event.status,
        external_id=event.external_id,
        sender=event.sender,
        recipient=event.recipient,
        occurred_at=event.occurred_at,
        subject=event.subject,
        body=event.body,
        ai_summary=event.ai_summary,
        metadata=json.loads(event.metadata_json or "{}"),
        created_by=event.created_by,
        created_at=event.created_at,
        updated_at=event.updated_at,
    )
