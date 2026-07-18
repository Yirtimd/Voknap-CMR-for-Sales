from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.tenancy import tenant_table_args


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = tenant_table_args("audit_logs", membership_columns=("user_id",))

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(120))
    entity_id: Mapped[str | None] = mapped_column(String(120))
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class FeatureFlag(Base):
    __tablename__ = "feature_flags"
    __table_args__ = tenant_table_args("feature_flags")

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    code: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class TenantPlan(Base):
    __tablename__ = "tenant_plans"
    __table_args__ = tenant_table_args("tenant_plans")

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    plan_code: Mapped[str] = mapped_column(String(80), default="trial")
    users_limit: Mapped[int] = mapped_column(default=5)
    leads_limit: Mapped[int] = mapped_column(default=500)
    documents_limit: Mapped[int] = mapped_column(default=50)
    ai_requests_limit: Mapped[int] = mapped_column(default=1000)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
