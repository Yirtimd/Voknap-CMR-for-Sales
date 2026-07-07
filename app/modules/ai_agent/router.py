import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import CurrentTenant, get_current_tenant
from app.modules.ai_agent.models import AgentAction
from app.modules.ai_agent.schemas import (
    AgentActionResponse,
    AgentChatRequest,
    AgentChatResponse,
    AgentHistoryMessage,
    CompanyCopilotResponse,
)
from app.modules.ai_agent.service import AgentService


router = APIRouter()


@router.get("/companies/{company_id}/copilot", response_model=CompanyCopilotResponse)
def company_copilot(
    company_id: UUID,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> CompanyCopilotResponse:
    service = AgentService(db)
    result = service.company_copilot(tenant.id, tenant.user_id, company_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return CompanyCopilotResponse(
        company_id=company_id,
        summary=result["summary"],
        next_best_action=result["next_best_action"],
        deal_risk=result["deal_risk"],
        follow_up_draft=result["follow_up_draft"],
        meeting_prep=result["meeting_prep"],
        insight=result["insight"],
        actions=[_action_response(action) for action in result["actions"]],
    )


@router.post("/chat", response_model=AgentChatResponse)
def chat(
    payload: AgentChatRequest,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> AgentChatResponse:
    service = AgentService(db)
    answer, actions, sources = service.chat(
        tenant_id=tenant.id,
        user_id=tenant.user_id,
        message=payload.message,
        company_id=payload.company_id,
        deal_id=payload.deal_id,
    )
    return AgentChatResponse(
        answer=answer,
        actions=[_action_response(action) for action in actions],
        sources=sources,
    )


@router.get("/history", response_model=list[AgentHistoryMessage])
def history(
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> list[AgentHistoryMessage]:
    service = AgentService(db)
    return [
        AgentHistoryMessage(
            id=message.id,
            role=message.role,
            content=message.content,
            created_at=message.created_at,
        )
        for message in service.list_history(tenant.id)
    ]


@router.get("/actions", response_model=list[AgentActionResponse])
def list_actions(
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> list[AgentActionResponse]:
    service = AgentService(db)
    return [_action_response(action) for action in service.list_actions(tenant.id)]


@router.post("/actions/{action_id}/confirm", response_model=AgentActionResponse)
def confirm_action(
    action_id: UUID,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> AgentActionResponse:
    service = AgentService(db)
    action = service.confirm_action(tenant.id, action_id)
    if action is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action not found")
    return _action_response(action)


@router.post("/actions/{action_id}/reject", response_model=AgentActionResponse)
def reject_action(
    action_id: UUID,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> AgentActionResponse:
    service = AgentService(db)
    action = service.reject_action(tenant.id, action_id)
    if action is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action not found")
    return _action_response(action)


def _action_response(action: AgentAction) -> AgentActionResponse:
    return AgentActionResponse(
        id=action.id,
        action_type=action.action_type,
        status=action.status,
        payload=json.loads(action.payload_json),
        result=json.loads(action.result_json) if action.result_json else None,
        created_at=action.created_at,
        confirmed_at=action.confirmed_at,
    )
