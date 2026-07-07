from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(80))
    email: Mapped[str | None] = mapped_column(String(255))
    company_name: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[str | None] = mapped_column(String(120))
    can_call: Mapped[bool] = mapped_column(Boolean, default=True)
    can_email: Mapped[bool] = mapped_column(Boolean, default=True)
    can_open_more: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    leads: Mapped[list["Lead"]] = relationship(back_populates="contact")


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    website: Mapped[str | None] = mapped_column(String(255))
    industry: Mapped[str | None] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default="active")
    company_type: Mapped[str | None] = mapped_column(String(40))
    health_score: Mapped[int | None] = mapped_column(Integer)
    client_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    owner_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    next_action_id: Mapped[UUID | None] = mapped_column(ForeignKey("next_actions.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Pipeline(Base):
    __tablename__ = "pipelines"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    stages: Mapped[list["PipelineStage"]] = relationship(
        back_populates="pipeline",
        cascade="all, delete-orphan",
        order_by="PipelineStage.sort_order",
    )


class PipelineStage(Base):
    __tablename__ = "pipeline_stages"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    pipeline_id: Mapped[UUID] = mapped_column(ForeignKey("pipelines.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    sort_order: Mapped[int] = mapped_column(default=0)

    pipeline: Mapped[Pipeline] = relationship(back_populates="stages")
    deals: Mapped[list["Deal"]] = relationship(back_populates="stage")


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    contact_id: Mapped[UUID | None] = mapped_column(ForeignKey("contacts.id"))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(80), default="new")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    contact: Mapped[Contact | None] = relationship(back_populates="leads")
    deals: Mapped[list["Deal"]] = relationship(back_populates="lead")
    notes: Mapped[list["Note"]] = relationship(back_populates="lead")


class Deal(Base):
    __tablename__ = "deals"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    lead_id: Mapped[UUID | None] = mapped_column(ForeignKey("leads.id"))
    stage_id: Mapped[UUID] = mapped_column(ForeignKey("pipeline_stages.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    amount: Mapped[float | None] = mapped_column(Numeric(12, 2))
    status: Mapped[str] = mapped_column(String(40), default="open")
    probability: Mapped[int | None] = mapped_column(Integer)
    expected_close_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expected_next_event: Mapped[str | None] = mapped_column(String(255))
    next_step: Mapped[str | None] = mapped_column(String(255))
    risk_level: Mapped[str | None] = mapped_column(String(40))
    forecast_category: Mapped[str | None] = mapped_column(String(40))
    owner_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    next_action_id: Mapped[UUID | None] = mapped_column(ForeignKey("next_actions.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    lead: Mapped[Lead | None] = relationship(back_populates="deals")
    stage: Mapped[PipelineStage] = relationship(back_populates="deals")
    tasks: Mapped[list["Task"]] = relationship(back_populates="deal")
    notes: Mapped[list["Note"]] = relationship(back_populates="deal")


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    assigned_to_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    deal_id: Mapped[UUID | None] = mapped_column(ForeignKey("deals.id"))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default="open")
    priority: Mapped[str] = mapped_column(String(40), default="normal")
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    deal: Mapped[Deal | None] = relationship(back_populates="tasks")


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    author_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    lead_id: Mapped[UUID | None] = mapped_column(ForeignKey("leads.id"))
    deal_id: Mapped[UUID | None] = mapped_column(ForeignKey("deals.id"))
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    lead: Mapped[Lead | None] = relationship(back_populates="notes")
    deal: Mapped[Deal | None] = relationship(back_populates="notes")


class NextAction(Base):
    __tablename__ = "next_actions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    deal_id: Mapped[UUID | None] = mapped_column(ForeignKey("deals.id"), index=True)
    contact_id: Mapped[UUID | None] = mapped_column(ForeignKey("contacts.id"), index=True)
    assigned_to_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(40), default="manual")
    status: Mapped[str] = mapped_column(String(40), default="open", index=True)
    priority: Mapped[str] = mapped_column(String(40), default="normal")
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class CompanyFile(Base):
    __tablename__ = "files"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    company_id: Mapped[UUID | None] = mapped_column(ForeignKey("companies.id"), index=True)
    deal_id: Mapped[UUID | None] = mapped_column(ForeignKey("deals.id"), index=True)
    contact_id: Mapped[UUID | None] = mapped_column(ForeignKey("contacts.id"), index=True)
    activity_id: Mapped[UUID | None] = mapped_column(ForeignKey("activities.id"), index=True)
    uploaded_by_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str | None] = mapped_column(String(40))
    mime_type: Mapped[str | None] = mapped_column(String(120))
    file_size: Mapped[int | None] = mapped_column(Integer)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    download_url: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class CustomerInsight(Base):
    __tablename__ = "customer_insights"
    __table_args__ = (UniqueConstraint("tenant_id", "company_id", name="uq_customer_insight_tenant_company"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    health_score: Mapped[int | None] = mapped_column(Integer)
    health_label: Mapped[str | None] = mapped_column(String(80))
    health_trend: Mapped[str | None] = mapped_column(String(20))
    risk_level: Mapped[str | None] = mapped_column(String(40))
    success_chance: Mapped[int | None] = mapped_column(Integer)
    success_chance_delta: Mapped[int | None] = mapped_column(Integer)
    ai_recommendations_json: Mapped[str] = mapped_column(Text, default="[]")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
