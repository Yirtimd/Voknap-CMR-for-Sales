import json
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.modules.accounts.models import Membership
from app.modules.activity.models import Activity
from app.modules.activity.service import ActivityService
from app.modules.automation.models import (
    ApprovalRequest,
    AutomationOutbox,
    AutomationRun,
    AutomationWorkflow,
    MessageTemplate,
)
from app.modules.automation.schemas import AutomationAction, AutomationCondition
from app.modules.communication.models import CommunicationEvent
from app.modules.sales.models import Company, Contact, Deal, Lead, NextAction, PipelineStage, Task


TRIGGER_FIELDS = {
    "lead.created": {"source", "status", "owner_id", "company_id", "title"},
    "deal.created": {
        "amount",
        "discount_percent",
        "status",
        "stage_id",
        "stage_name",
        "owner_id",
        "company_id",
    },
    "deal.updated": {
        "amount",
        "discount_percent",
        "status",
        "stage_id",
        "stage_name",
        "owner_id",
        "company_id",
        "changed_fields",
    },
    "deal.stage_changed": {
        "amount",
        "discount_percent",
        "status",
        "old_stage_id",
        "stage_id",
        "stage_name",
        "owner_id",
        "company_id",
    },
    "communication.created": {
        "channel",
        "direction",
        "status",
        "sender",
        "recipient",
        "company_id",
        "contact_id",
        "deal_id",
        "subject",
    },
    "schedule.deal_inactive": {
        "inactive_days",
        "amount",
        "discount_percent",
        "status",
        "stage_id",
        "stage_name",
        "owner_id",
        "company_id",
    },
}
ACTION_TYPES = {
    "assign_owner",
    "create_task",
    "send_template",
    "request_approval",
    "update_next_action",
}
TRIGGER_ACTIONS = {
    "lead.created": ACTION_TYPES,
    "deal.created": ACTION_TYPES,
    "deal.updated": ACTION_TYPES,
    "deal.stage_changed": ACTION_TYPES,
    "communication.created": ACTION_TYPES - {"assign_owner"},
    "schedule.deal_inactive": ACTION_TYPES,
}
_PLACEHOLDER = re.compile(r"{{\s*([a-z][a-z0-9_.]*)\s*}}")


class AutomationEngine:
    def __init__(self, db: Session):
        self.db = db

    def validate_workflow(
        self,
        tenant_id: UUID,
        trigger_type: str,
        conditions: list[AutomationCondition],
        actions: list[AutomationAction],
    ) -> None:
        invalid_fields = {condition.field for condition in conditions} - TRIGGER_FIELDS[trigger_type]
        if invalid_fields:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unsupported trigger fields: {', '.join(sorted(invalid_fields))}",
            )
        invalid_actions = {action.type for action in actions} - TRIGGER_ACTIONS[trigger_type]
        if invalid_actions:
            raise HTTPException(
                status_code=422,
                detail=f"Unsupported trigger actions: {', '.join(sorted(invalid_actions))}",
            )
        self._validate_actions(tenant_id, actions)

    def emit(
        self,
        *,
        tenant_id: UUID,
        trigger_type: str,
        entity_type: str,
        entity_id: UUID,
        event_key: str,
        context: dict[str, Any],
        actor_id: UUID | None,
    ) -> list[AutomationRun]:
        workflows = (
            self.db.query(AutomationWorkflow)
            .filter(
                AutomationWorkflow.tenant_id == tenant_id,
                AutomationWorkflow.trigger_type == trigger_type,
                AutomationWorkflow.is_active.is_(True),
            )
            .order_by(AutomationWorkflow.priority, AutomationWorkflow.created_at)
            .all()
        )
        runs = []
        for workflow in workflows:
            conditions = [AutomationCondition.model_validate(item) for item in _load(workflow.conditions_json)]
            if not _conditions_match(conditions, workflow.condition_logic, context):
                continue
            existing = (
                self.db.query(AutomationRun.id)
                .filter(
                    AutomationRun.tenant_id == tenant_id,
                    AutomationRun.workflow_id == workflow.id,
                    AutomationRun.event_key == event_key,
                )
                .first()
            )
            if existing is not None:
                continue
            run = AutomationRun(
                tenant_id=tenant_id,
                workflow_id=workflow.id,
                event_key=event_key[:255],
                trigger_type=trigger_type,
                entity_type=entity_type,
                entity_id=entity_id,
                actor_id=actor_id,
                context_json=_dump(context),
            )
            self.db.add(run)
            self.db.flush()
            try:
                with self.db.begin_nested():
                    actions = [AutomationAction.model_validate(item) for item in _load(workflow.actions_json)]
                    results = self._execute_actions(workflow, run, context, actions, actor_id)
                run.status = "succeeded"
                run.result_json = _dump(results)
            except Exception as error:  # workflow failure must not abort source CRM transaction
                run.status = "failed"
                run.error = str(error)[:4000]
            run.completed_at = _now()
            runs.append(run)
        return runs

    def run_scheduled(self, tenant_id: UUID, actor_id: UUID | None) -> tuple[int, int]:
        deals = (
            self.db.query(Deal)
            .filter(
                Deal.tenant_id == tenant_id,
                Deal.status == "open",
                Deal.deleted_at.is_(None),
                Deal.is_archived.is_(False),
            )
            .all()
        )
        run_count = 0
        now = _now()
        for deal in deals:
            last_activity = (
                self.db.query(func.max(Activity.created_at))
                .filter(Activity.tenant_id == tenant_id, Activity.deal_id == deal.id)
                .scalar()
            )
            activity_at = _as_utc(last_activity or deal.created_at)
            inactive_days = max(0, (now - activity_at).days)
            context = self.deal_context(deal)
            context["inactive_days"] = inactive_days
            event_key = f"inactive:{deal.id}:{activity_at.isoformat()}"
            run_count += len(
                self.emit(
                    tenant_id=tenant_id,
                    trigger_type="schedule.deal_inactive",
                    entity_type="deal",
                    entity_id=deal.id,
                    event_key=event_key,
                    context=context,
                    actor_id=actor_id,
                )
            )
        self.db.commit()
        return len(deals), run_count

    def decide_approval(
        self,
        approval: ApprovalRequest,
        decision: str,
        decided_by_id: UUID,
        comment: str | None,
    ) -> None:
        if approval.status != "pending":
            raise HTTPException(status_code=409, detail="Approval is already decided")
        if approval.assigned_to_id not in {None, decided_by_id}:
            raise HTTPException(status_code=403, detail="Approval is assigned to another user")
        if decision == "approved":
            actions = [AutomationAction.model_validate(item) for item in _load(approval.continuation_json)]
            if actions:
                workflow = self.db.get(AutomationWorkflow, approval.workflow_id)
                run = self.db.get(AutomationRun, approval.run_id)
                if workflow is None or run is None:
                    raise HTTPException(status_code=409, detail="Approval workflow is unavailable")
                context = _load(run.context_json)
                context["approval_id"] = str(approval.id)
                results = self._execute_actions(workflow, run, context, actions, decided_by_id)
                existing = _load(run.result_json)
                run.result_json = _dump([*existing, {"approval_continuation": results}])
        approval.status = decision
        approval.decision_comment = comment
        approval.decided_by_id = decided_by_id
        approval.decided_at = _now()
        self.db.commit()

    def deal_context(self, deal: Deal) -> dict[str, Any]:
        stage = self.db.get(PipelineStage, deal.stage_id)
        return {
            "amount": float(deal.amount) if deal.amount is not None else None,
            "discount_percent": deal.discount_percent,
            "status": deal.status,
            "stage_id": str(deal.stage_id),
            "stage_name": stage.name if stage else None,
            "owner_id": str(deal.owner_id) if deal.owner_id else None,
            "company_id": str(deal.company_id),
            "title": deal.title,
        }

    def _execute_actions(
        self,
        workflow: AutomationWorkflow,
        run: AutomationRun,
        context: dict[str, Any],
        actions: list[AutomationAction],
        actor_id: UUID | None,
    ) -> list[dict]:
        results = []
        for action in actions:
            if action.type == "assign_owner":
                results.append(self._assign_owner(run, context, action.config, actor_id))
            elif action.type == "create_task":
                results.append(self._create_task(run, context, action.config, actor_id))
            elif action.type == "send_template":
                results.append(self._queue_template(run, context, action.config))
            elif action.type == "request_approval":
                results.append(self._request_approval(workflow, run, context, action.config, actor_id))
            else:
                results.append(self._update_next_action(run, context, action.config, actor_id))
        return results

    def _assign_owner(
        self,
        run: AutomationRun,
        context: dict[str, Any],
        config: dict[str, Any],
        actor_id: UUID | None,
    ) -> dict:
        entity = self._get_entity(run)
        owner_id = self._resolve_user(run.tenant_id, entity, config, actor_id)
        entity.owner_id = owner_id
        context["owner_id"] = str(owner_id)
        return {"type": "assign_owner", "owner_id": str(owner_id)}

    def _create_task(
        self,
        run: AutomationRun,
        context: dict[str, Any],
        config: dict[str, Any],
        actor_id: UUID | None,
    ) -> dict:
        entity = self._get_entity(run)
        company_id = getattr(entity, "company_id", None)
        if company_id is None:
            raise ValueError("Task action requires company context")
        assigned_to_id = self._resolve_user(run.tenant_id, entity, config, actor_id)
        task = Task(
            tenant_id=run.tenant_id,
            company_id=company_id,
            deal_id=entity.id if isinstance(entity, Deal) else context.get("deal_id"),
            assigned_to_id=assigned_to_id,
            title=_render(config["title"], context),
            description=_render(config.get("description"), context),
            priority=config.get("priority", "normal"),
            due_at=_now() + timedelta(days=int(config.get("due_in_days", 0))),
        )
        self.db.add(task)
        self.db.flush()
        ActivityService(self.db).create(
            tenant_id=run.tenant_id,
            created_by=actor_id,
            company_id=company_id,
            deal_id=task.deal_id,
            activity_type="AUTOMATION",
            title="Automation created task",
            description=task.title,
            metadata={"workflow_id": str(run.workflow_id), "run_id": str(run.id)},
            commit=False,
        )
        return {"type": "create_task", "task_id": str(task.id)}

    def _queue_template(
        self,
        run: AutomationRun,
        context: dict[str, Any],
        config: dict[str, Any],
    ) -> dict:
        template = (
            self.db.query(MessageTemplate)
            .filter(
                MessageTemplate.tenant_id == run.tenant_id,
                MessageTemplate.id == UUID(str(config["template_id"])),
                MessageTemplate.is_active.is_(True),
            )
            .one_or_none()
        )
        if template is None:
            raise ValueError("Active message template not found")
        recipient = self._resolve_recipient(run, context, config)
        row = AutomationOutbox(
            tenant_id=run.tenant_id,
            run_id=run.id,
            template_id=template.id,
            entity_type=run.entity_type,
            entity_id=run.entity_id,
            channel=template.channel,
            recipient=recipient,
            subject=_render(template.subject, context) or "",
            body=_render(template.body, context) or "",
        )
        self.db.add(row)
        self.db.flush()
        return {"type": "send_template", "outbox_id": str(row.id), "status": "pending"}

    def _request_approval(
        self,
        workflow: AutomationWorkflow,
        run: AutomationRun,
        context: dict[str, Any],
        config: dict[str, Any],
        actor_id: UUID | None,
    ) -> dict:
        entity = self._get_entity(run)
        assigned_to_id = self._resolve_user(run.tenant_id, entity, config, actor_id)
        continuation = [AutomationAction.model_validate(item) for item in config.get("on_approve", [])]
        approval = ApprovalRequest(
            tenant_id=run.tenant_id,
            workflow_id=workflow.id,
            run_id=run.id,
            entity_type=run.entity_type,
            entity_id=run.entity_id,
            title=_render(config["title"], context) or "Approval required",
            reason=_render(config.get("reason"), context),
            requested_by_id=actor_id,
            assigned_to_id=assigned_to_id,
            continuation_json=_dump([item.model_dump(mode="json") for item in continuation]),
        )
        self.db.add(approval)
        self.db.flush()
        return {"type": "request_approval", "approval_id": str(approval.id)}

    def _update_next_action(
        self,
        run: AutomationRun,
        context: dict[str, Any],
        config: dict[str, Any],
        actor_id: UUID | None,
    ) -> dict:
        entity = self._get_entity(run)
        company_id = getattr(entity, "company_id", None) or getattr(entity, "id", None)
        if isinstance(entity, CommunicationEvent):
            company_id = entity.company_id
        if company_id is None:
            raise ValueError("Next action requires linked company")
        deal_id = entity.id if isinstance(entity, Deal) else getattr(entity, "deal_id", None)
        owner_source = entity
        if isinstance(entity, CommunicationEvent) and entity.deal_id:
            owner_source = self.db.get(Deal, entity.deal_id) or entity
        elif isinstance(entity, CommunicationEvent) and entity.company_id:
            owner_source = self.db.get(Company, entity.company_id) or entity
        assigned_to_id = self._resolve_user(run.tenant_id, owner_source, config, actor_id)
        company = self.db.get(Company, company_id)
        deal = self.db.get(Deal, deal_id) if deal_id else None
        if company and company.next_action_id:
            previous = self.db.get(NextAction, company.next_action_id)
            if previous and previous.status == "open":
                previous.status = "superseded"
                previous.completed_at = _now()
        next_action = NextAction(
            tenant_id=run.tenant_id,
            company_id=company_id,
            deal_id=deal_id,
            contact_id=getattr(entity, "contact_id", None),
            assigned_to_id=assigned_to_id,
            title=_render(config["title"], context) or "Follow up",
            description=_render(config.get("description"), context),
            source="automation",
            priority=config.get("priority", "normal"),
            due_at=_now() + timedelta(days=int(config.get("due_in_days", 0))),
        )
        self.db.add(next_action)
        self.db.flush()
        if company:
            company.next_action_id = next_action.id
        if deal:
            deal.next_action_id = next_action.id
            deal.next_step = next_action.title
        return {"type": "update_next_action", "next_action_id": str(next_action.id)}

    def _resolve_user(
        self,
        tenant_id: UUID,
        entity: Any,
        config: dict[str, Any],
        actor_id: UUID | None,
    ) -> UUID:
        mode = config.get("assignee", "owner")
        if config.get("user_id"):
            user_id = UUID(str(config["user_id"]))
        elif mode == "actor":
            user_id = actor_id
        else:
            owner_id = getattr(entity, "owner_id", None)
            if mode == "owner":
                user_id = owner_id
            elif mode == "owner_manager":
                owner_membership = (
                    self.db.query(Membership)
                    .filter(
                        Membership.tenant_id == tenant_id,
                        Membership.user_id == owner_id,
                        Membership.is_active.is_(True),
                    )
                    .one_or_none()
                )
                manager = (
                    self.db.get(Membership, owner_membership.manager_membership_id)
                    if owner_membership and owner_membership.manager_membership_id
                    else None
                )
                user_id = manager.user_id if manager and manager.is_active else None
            else:
                raise ValueError("Unsupported assignee mode")
        if user_id is None:
            raise ValueError("Automation could not resolve assignee")
        membership = (
            self.db.query(Membership)
            .filter(
                Membership.tenant_id == tenant_id,
                Membership.user_id == user_id,
                Membership.is_active.is_(True),
            )
            .one_or_none()
        )
        if membership is None:
            raise ValueError("Automation assignee is not an active tenant member")
        return user_id

    def _resolve_recipient(
        self,
        run: AutomationRun,
        context: dict[str, Any],
        config: dict[str, Any],
    ) -> str:
        if config.get("recipient"):
            return _render(str(config["recipient"]), context) or ""
        field = config.get("recipient_field", "contact_email")
        if field in {"sender", "recipient"} and context.get(field):
            return str(context[field])
        entity = self._get_entity(run)
        contact_id = getattr(entity, "contact_id", None)
        company_id = getattr(entity, "company_id", None)
        query = self.db.query(Contact).filter(Contact.tenant_id == run.tenant_id)
        contact = query.filter(Contact.id == contact_id).one_or_none() if contact_id else None
        if contact is None and company_id:
            contact = query.filter(Contact.company_id == company_id, Contact.email.is_not(None)).first()
        if contact is None or not contact.email:
            raise ValueError("Template action could not resolve recipient")
        return contact.email

    def _get_entity(self, run: AutomationRun) -> Any:
        model = {"lead": Lead, "deal": Deal, "communication": CommunicationEvent}.get(run.entity_type)
        if model is None:
            raise ValueError("Unsupported automation entity")
        entity = (
            self.db.query(model)
            .filter(model.tenant_id == run.tenant_id, model.id == run.entity_id)
            .one_or_none()
        )
        if entity is None:
            raise ValueError("Automation entity not found")
        return entity

    def _validate_actions(self, tenant_id: UUID, actions: list[AutomationAction]) -> None:
        for action in actions:
            if action.type not in ACTION_TYPES:
                raise HTTPException(status_code=422, detail="Unsupported action")
            config = action.config
            if action.type in {"create_task", "update_next_action", "request_approval"}:
                if not config.get("title"):
                    raise HTTPException(status_code=422, detail=f"{action.type} requires title")
            if action.type == "send_template":
                try:
                    template_id = UUID(str(config["template_id"]))
                except (KeyError, ValueError):
                    raise HTTPException(status_code=422, detail="send_template requires template_id") from None
                template = (
                    self.db.query(MessageTemplate.id)
                    .filter(MessageTemplate.tenant_id == tenant_id, MessageTemplate.id == template_id)
                    .first()
                )
                if template is None:
                    raise HTTPException(status_code=404, detail="Message template not found")
            if config.get("user_id"):
                try:
                    user_id = UUID(str(config["user_id"]))
                except ValueError:
                    raise HTTPException(status_code=422, detail="user_id must be UUID") from None
                member = (
                    self.db.query(Membership.id)
                    .filter(
                        Membership.tenant_id == tenant_id,
                        Membership.user_id == user_id,
                        Membership.is_active.is_(True),
                    )
                    .first()
                )
                if member is None:
                    raise HTTPException(status_code=404, detail="Active automation assignee not found")
            due_days = config.get("due_in_days", 0)
            if not isinstance(due_days, int) or not 0 <= due_days <= 365:
                raise HTTPException(status_code=422, detail="due_in_days must be between 0 and 365")
            if action.type == "request_approval":
                continuation = [AutomationAction.model_validate(item) for item in config.get("on_approve", [])]
                if any(item.type == "request_approval" for item in continuation):
                    raise HTTPException(status_code=422, detail="Nested approvals are not supported")
                self._validate_actions(tenant_id, continuation)


def _conditions_match(
    conditions: list[AutomationCondition],
    logic: str,
    context: dict[str, Any],
) -> bool:
    if not conditions:
        return True
    results = [_condition_matches(condition, context.get(condition.field)) for condition in conditions]
    return any(results) if logic == "any" else all(results)


def _condition_matches(condition: AutomationCondition, actual: Any) -> bool:
    expected = condition.value
    if condition.operator == "is_empty":
        return actual is None or actual == "" or actual == []
    if condition.operator == "contains":
        if isinstance(actual, list):
            return expected in actual
        return str(expected).casefold() in str(actual or "").casefold()
    if condition.operator == "in":
        return actual in (expected or [])
    left, right = _comparable(actual), _comparable(expected)
    if condition.operator == "eq":
        return left == right
    if condition.operator == "neq":
        return left != right
    if left is None or right is None:
        return False
    if condition.operator == "gt":
        return left > right
    if condition.operator == "gte":
        return left >= right
    if condition.operator == "lt":
        return left < right
    return left <= right


def _comparable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, str):
        return value.casefold()
    return value


def _render(template: str | None, context: dict[str, Any]) -> str | None:
    if template is None:
        return None
    return _PLACEHOLDER.sub(lambda match: str(context.get(match.group(1), "")), template)


def _load(value: str) -> Any:
    return json.loads(value or "[]")


def _dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
