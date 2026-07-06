from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
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
