from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ConnectorAccount(Base):
    __tablename__ = "connector_accounts"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    connector_code: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="connected")
    credentials_json: Mapped[str] = mapped_column(Text, default="{}")
    settings_json: Mapped[str] = mapped_column(Text, default="{}")
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ConnectorSyncRun(Base):
    __tablename__ = "connector_sync_runs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    account_id: Mapped[UUID] = mapped_column(ForeignKey("connector_accounts.id"), nullable=False)
    direction: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="success")
    created_count: Mapped[int] = mapped_column(default=0)
    updated_count: Mapped[int] = mapped_column(default=0)
    failed_count: Mapped[int] = mapped_column(default=0)
    message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

