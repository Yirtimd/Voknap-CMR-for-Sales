import json
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.accounts.models import Membership
from app.modules.ai_agent.models import AgentMessage
from app.modules.connectors.models import ConnectorAccount
from app.modules.knowledge.models import KnowledgeDocument
from app.modules.production.models import AuditLog, FeatureFlag, TenantPlan
from app.modules.sales.models import Contact, Deal, Lead, Task
from app.modules.templates.models import AppliedTemplate


class ProductionService:
    def __init__(self, db: Session):
        self.db = db

    def overview(self, tenant_id: UUID) -> dict:
        plan = self.get_or_create_plan(tenant_id)
        flags = self.list_flags(tenant_id)
        return {
            "tenant_id": tenant_id,
            "counts": self.counts(tenant_id),
            "plan": self._plan_dict(plan),
            "flags": [self._flag_dict(flag) for flag in flags],
        }

    def counts(self, tenant_id: UUID) -> dict[str, int]:
        return {
            "users": self.db.query(Membership).filter(Membership.tenant_id == tenant_id).count(),
            "contacts": self.db.query(Contact).filter(Contact.tenant_id == tenant_id).count(),
            "leads": self.db.query(Lead).filter(Lead.tenant_id == tenant_id).count(),
            "deals": self.db.query(Deal).filter(Deal.tenant_id == tenant_id).count(),
            "tasks": self.db.query(Task).filter(Task.tenant_id == tenant_id).count(),
            "documents": self.db.query(KnowledgeDocument).filter(KnowledgeDocument.tenant_id == tenant_id).count(),
            "agent_messages": self.db.query(AgentMessage).filter(AgentMessage.tenant_id == tenant_id).count(),
            "connectors": self.db.query(ConnectorAccount).filter(ConnectorAccount.tenant_id == tenant_id).count(),
        }

    def log(
        self,
        tenant_id: UUID,
        user_id: UUID | None,
        action: str,
        entity_type: str | None = None,
        entity_id: str | None = None,
        payload: dict | None = None,
    ) -> AuditLog:
        row = AuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            payload_json=json.dumps(payload or {}),
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_audit(self, tenant_id: UUID, limit: int = 50) -> list[AuditLog]:
        return (
            self.db.query(AuditLog)
            .filter(AuditLog.tenant_id == tenant_id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
            .all()
        )

    def list_flags(self, tenant_id: UUID) -> list[FeatureFlag]:
        return (
            self.db.query(FeatureFlag)
            .filter(FeatureFlag.tenant_id == tenant_id)
            .order_by(FeatureFlag.created_at.desc())
            .all()
        )

    def create_flag(self, tenant_id: UUID, code: str, title: str, enabled: bool) -> FeatureFlag:
        existing = (
            self.db.query(FeatureFlag)
            .filter(FeatureFlag.tenant_id == tenant_id, FeatureFlag.code == code)
            .one_or_none()
        )
        if existing:
            existing.title = title
            existing.enabled = enabled
            self.db.commit()
            self.db.refresh(existing)
            return existing

        flag = FeatureFlag(tenant_id=tenant_id, code=code, title=title, enabled=enabled)
        self.db.add(flag)
        self.db.commit()
        self.db.refresh(flag)
        return flag

    def update_flag(self, tenant_id: UUID, flag_id: UUID, enabled: bool) -> FeatureFlag | None:
        flag = (
            self.db.query(FeatureFlag)
            .filter(FeatureFlag.id == flag_id, FeatureFlag.tenant_id == tenant_id)
            .one_or_none()
        )
        if not flag:
            return None
        flag.enabled = enabled
        self.db.commit()
        self.db.refresh(flag)
        return flag

    def get_or_create_plan(self, tenant_id: UUID) -> TenantPlan:
        plan = self.db.query(TenantPlan).filter(TenantPlan.tenant_id == tenant_id).one_or_none()
        if plan:
            return plan
        plan = TenantPlan(tenant_id=tenant_id)
        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)
        return plan

    def update_plan(self, tenant_id: UUID, payload) -> TenantPlan:
        plan = self.get_or_create_plan(tenant_id)
        plan.plan_code = payload.plan_code
        plan.users_limit = payload.users_limit
        plan.leads_limit = payload.leads_limit
        plan.documents_limit = payload.documents_limit
        plan.ai_requests_limit = payload.ai_requests_limit
        self.db.commit()
        self.db.refresh(plan)
        return plan

    def export_tenant_data(self, tenant_id: UUID) -> dict:
        return {
            "counts": self.counts(tenant_id),
            "contacts": [self._simple_dict(row) for row in self.db.query(Contact).filter(Contact.tenant_id == tenant_id).all()],
            "leads": [self._simple_dict(row) for row in self.db.query(Lead).filter(Lead.tenant_id == tenant_id).all()],
            "deals": [self._simple_dict(row) for row in self.db.query(Deal).filter(Deal.tenant_id == tenant_id).all()],
            "tasks": [self._simple_dict(row) for row in self.db.query(Task).filter(Task.tenant_id == tenant_id).all()],
            "documents": [self._simple_dict(row) for row in self.db.query(KnowledgeDocument).filter(KnowledgeDocument.tenant_id == tenant_id).all()],
            "templates": [self._simple_dict(row) for row in self.db.query(AppliedTemplate).filter(AppliedTemplate.tenant_id == tenant_id).all()],
        }

    def _simple_dict(self, row) -> dict:
        data = {}
        for column in row.__table__.columns:
            value = getattr(row, column.name)
            data[column.name] = str(value) if value is not None else None
        return data

    def _flag_dict(self, flag: FeatureFlag) -> dict:
        return {"id": str(flag.id), "code": flag.code, "title": flag.title, "enabled": flag.enabled}

    def _plan_dict(self, plan: TenantPlan) -> dict:
        return {
            "id": str(plan.id),
            "plan_code": plan.plan_code,
            "users_limit": plan.users_limit,
            "leads_limit": plan.leads_limit,
            "documents_limit": plan.documents_limit,
            "ai_requests_limit": plan.ai_requests_limit,
        }
