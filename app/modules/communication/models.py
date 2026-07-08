from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CommunicationEvent(Base):
    __tablename__ = "communication_events"
    __table_args__ = (
        UniqueConstraint("tenant_id", "channel", "external_id", name="uq_communication_event_external"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    company_id: Mapped[UUID | None] = mapped_column(ForeignKey("companies.id"), index=True)
    contact_id: Mapped[UUID | None] = mapped_column(ForeignKey("contacts.id"), index=True)
    deal_id: Mapped[UUID | None] = mapped_column(ForeignKey("deals.id"), index=True)
    activity_id: Mapped[UUID | None] = mapped_column(ForeignKey("activities.id"), index=True)
    connector_account_id: Mapped[UUID | None] = mapped_column(ForeignKey("connector_accounts.id"), index=True)
    channel: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    direction: Mapped[str] = mapped_column(String(20), default="inbound", index=True)
    status: Mapped[str] = mapped_column(String(40), default="new", index=True)
    external_id: Mapped[str | None] = mapped_column(String(255), index=True)
    sender: Mapped[str | None] = mapped_column(String(255))
    recipient: Mapped[str | None] = mapped_column(String(255))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    ai_summary: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_by: Mapped[UUID | None] = mapped_column(index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
