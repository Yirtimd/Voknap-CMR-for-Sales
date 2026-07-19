import json
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from app.core.database import get_db
from app.core.dependencies import CurrentTenant
from app.core.rbac import Permission, require_permission
from app.modules.automation.models import (
    ApprovalRequest,
    AutomationOutbox,
    AutomationRun,
    AutomationWorkflow,
    MessageTemplate,
)
from app.modules.automation.schemas import (
    ApprovalDecision,
    ApprovalResponse,
    AutomationAction,
    AutomationCondition,
    AutomationRunResponse,
    MessageTemplateCreate,
    MessageTemplateResponse,
    MessageTemplateUpdate,
    OutboxResponse,
    OutboxStatusUpdate,
    ScheduledRunResponse,
    WorkflowCreate,
    WorkflowResponse,
    WorkflowUpdate,
)
from app.modules.automation.service import AutomationEngine


router = APIRouter()


@router.post("/workflows", response_model=WorkflowResponse, status_code=201)
def create_workflow(
    payload: WorkflowCreate,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(require_permission(Permission.AUTOMATIONS_MANAGE)),
) -> WorkflowResponse:
    engine = AutomationEngine(db)
    engine.validate_workflow(tenant.id, payload.trigger_type, payload.conditions, payload.actions)
    workflow = AutomationWorkflow(
        tenant_id=tenant.id,
        name=payload.name,
        description=payload.description,
        trigger_type=payload.trigger_type,
        conditions_json=_dump_models(payload.conditions),
        condition_logic=payload.condition_logic,
        actions_json=_dump_models(payload.actions),
        priority=payload.priority,
        is_active=payload.is_active,
        created_by_id=tenant.user_id,
        updated_by_id=tenant.user_id,
    )
    db.add(workflow)
    db.commit()
    db.refresh(workflow)
    return _workflow_response(workflow)


@router.get("/workflows", response_model=list[WorkflowResponse])
def list_workflows(
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(require_permission(Permission.AUTOMATIONS_MANAGE)),
) -> list[WorkflowResponse]:
    rows = (
        db.query(AutomationWorkflow)
        .filter(AutomationWorkflow.tenant_id == tenant.id)
        .order_by(AutomationWorkflow.priority, AutomationWorkflow.created_at)
        .all()
    )
    return [_workflow_response(row) for row in rows]


@router.patch("/workflows/{workflow_id}", response_model=WorkflowResponse)
def update_workflow(
    workflow_id: UUID,
    payload: WorkflowUpdate,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(require_permission(Permission.AUTOMATIONS_MANAGE)),
) -> WorkflowResponse:
    workflow = _get(db, AutomationWorkflow, tenant.id, workflow_id, "Workflow")
    if workflow.version != payload.version:
        raise HTTPException(
            status_code=409,
            detail={"message": "Version conflict", "current_version": workflow.version},
        )
    trigger_type = payload.trigger_type or workflow.trigger_type
    conditions = (
        payload.conditions
        if payload.conditions is not None
        else [
            AutomationCondition.model_validate(item)
            for item in json.loads(workflow.conditions_json)
        ]
    )
    actions = (
        payload.actions
        if payload.actions is not None
        else [AutomationAction.model_validate(item) for item in json.loads(workflow.actions_json)]
    )
    AutomationEngine(db).validate_workflow(tenant.id, trigger_type, conditions, actions)
    changes = payload.model_dump(exclude={"version", "conditions", "actions"}, exclude_unset=True)
    for key, value in changes.items():
        setattr(workflow, key, value)
    if payload.conditions is not None:
        workflow.conditions_json = _dump_models(payload.conditions)
    if payload.actions is not None:
        workflow.actions_json = _dump_models(payload.actions)
    workflow.updated_by_id = tenant.user_id
    try:
        db.commit()
        db.refresh(workflow)
    except StaleDataError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="Workflow was changed by another request") from error
    return _workflow_response(workflow)


@router.post("/templates", response_model=MessageTemplateResponse, status_code=201)
def create_message_template(
    payload: MessageTemplateCreate,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(require_permission(Permission.AUTOMATIONS_MANAGE)),
) -> MessageTemplate:
    row = MessageTemplate(tenant_id=tenant.id, created_by_id=tenant.user_id, **payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/templates", response_model=list[MessageTemplateResponse])
def list_message_templates(
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(require_permission(Permission.AUTOMATIONS_MANAGE)),
) -> list[MessageTemplate]:
    return (
        db.query(MessageTemplate)
        .filter(MessageTemplate.tenant_id == tenant.id)
        .order_by(MessageTemplate.name)
        .all()
    )


@router.patch("/templates/{template_id}", response_model=MessageTemplateResponse)
def update_message_template(
    template_id: UUID,
    payload: MessageTemplateUpdate,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(require_permission(Permission.AUTOMATIONS_MANAGE)),
) -> MessageTemplate:
    row = _get(db, MessageTemplate, tenant.id, template_id, "Message template")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


@router.get("/runs", response_model=list[AutomationRunResponse])
def list_runs(
    workflow_id: UUID | None = None,
    run_status: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(require_permission(Permission.AUTOMATIONS_MANAGE)),
) -> list[AutomationRunResponse]:
    query = db.query(AutomationRun).filter(AutomationRun.tenant_id == tenant.id)
    if workflow_id:
        query = query.filter(AutomationRun.workflow_id == workflow_id)
    if run_status:
        query = query.filter(AutomationRun.status == run_status)
    return [_run_response(row) for row in query.order_by(AutomationRun.started_at.desc()).limit(limit)]


@router.post("/run-scheduled", response_model=ScheduledRunResponse)
def run_scheduled_automations(
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(require_permission(Permission.AUTOMATIONS_MANAGE)),
) -> ScheduledRunResponse:
    evaluated, matched = AutomationEngine(db).run_scheduled(tenant.id, tenant.user_id)
    return ScheduledRunResponse(evaluated=evaluated, matched_runs=matched)


@router.get("/approvals", response_model=list[ApprovalResponse])
def list_approvals(
    approval_status: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(require_permission(Permission.APPROVALS_MANAGE)),
) -> list[ApprovalResponse]:
    query = db.query(ApprovalRequest).filter(ApprovalRequest.tenant_id == tenant.id)
    if approval_status:
        query = query.filter(ApprovalRequest.status == approval_status)
    return [_approval_response(row) for row in query.order_by(ApprovalRequest.created_at.desc())]


@router.post("/approvals/{approval_id}/decision", response_model=ApprovalResponse)
def decide_approval(
    approval_id: UUID,
    payload: ApprovalDecision,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(require_permission(Permission.APPROVALS_MANAGE)),
) -> ApprovalResponse:
    approval = _get(db, ApprovalRequest, tenant.id, approval_id, "Approval")
    AutomationEngine(db).decide_approval(
        approval,
        payload.decision,
        tenant.user_id,
        payload.comment,
    )
    db.refresh(approval)
    return _approval_response(approval)


@router.get("/outbox", response_model=list[OutboxResponse])
def list_outbox(
    outbox_status: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(require_permission(Permission.AUTOMATIONS_MANAGE)),
) -> list[AutomationOutbox]:
    query = db.query(AutomationOutbox).filter(AutomationOutbox.tenant_id == tenant.id)
    if outbox_status:
        query = query.filter(AutomationOutbox.status == outbox_status)
    return query.order_by(AutomationOutbox.created_at.desc()).all()


@router.patch("/outbox/{outbox_id}", response_model=OutboxResponse)
def update_outbox_status(
    outbox_id: UUID,
    payload: OutboxStatusUpdate,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(require_permission(Permission.AUTOMATIONS_MANAGE)),
) -> AutomationOutbox:
    row = _get(db, AutomationOutbox, tenant.id, outbox_id, "Outbox item")
    if row.status not in {"pending", "sending", "failed"}:
        raise HTTPException(status_code=409, detail="Outbox item is final")
    row.status = payload.status
    row.last_error = payload.error
    row.attempts += 1
    row.sent_at = datetime.now(timezone.utc) if payload.status == "sent" else None
    db.commit()
    db.refresh(row)
    return row


def _get(db: Session, model, tenant_id: UUID, object_id: UUID, label: str):
    row = db.query(model).filter(model.tenant_id == tenant_id, model.id == object_id).one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label} not found")
    return row


def _workflow_response(workflow: AutomationWorkflow) -> WorkflowResponse:
    return WorkflowResponse(
        id=workflow.id,
        name=workflow.name,
        description=workflow.description,
        trigger_type=workflow.trigger_type,
        conditions=[AutomationCondition.model_validate(item) for item in json.loads(workflow.conditions_json)],
        condition_logic=workflow.condition_logic,
        actions=[AutomationAction.model_validate(item) for item in json.loads(workflow.actions_json)],
        priority=workflow.priority,
        is_active=workflow.is_active,
        version=workflow.version,
        created_by_id=workflow.created_by_id,
        updated_by_id=workflow.updated_by_id,
        created_at=workflow.created_at,
        updated_at=workflow.updated_at,
    )


def _run_response(run: AutomationRun) -> AutomationRunResponse:
    return AutomationRunResponse(
        id=run.id,
        workflow_id=run.workflow_id,
        event_key=run.event_key,
        trigger_type=run.trigger_type,
        entity_type=run.entity_type,
        entity_id=run.entity_id,
        actor_id=run.actor_id,
        status=run.status,
        result=json.loads(run.result_json),
        error=run.error,
        started_at=run.started_at,
        completed_at=run.completed_at,
    )


def _approval_response(row: ApprovalRequest) -> ApprovalResponse:
    return ApprovalResponse(
        id=row.id,
        workflow_id=row.workflow_id,
        run_id=row.run_id,
        entity_type=row.entity_type,
        entity_id=row.entity_id,
        title=row.title,
        reason=row.reason,
        requested_by_id=row.requested_by_id,
        assigned_to_id=row.assigned_to_id,
        status=row.status,
        decision_comment=row.decision_comment,
        decided_by_id=row.decided_by_id,
        decided_at=row.decided_at,
        created_at=row.created_at,
    )


def _dump_models(rows: list) -> str:
    return json.dumps([row.model_dump(mode="json") for row in rows], ensure_ascii=False)
