from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from alembic import command
from alembic.config import Config
from sqlalchemy import Boolean, DateTime, Integer, String, inspect, text
from sqlalchemy.orm import Session

from app.core.database import Base, SessionLocal, engine
from app.core.config import settings
from app.core.security import hash_password
from app.modules.accounts.models import Membership, Tenant, User
from app.modules.sales import models as sales_models


DEV_TENANT_NAME = "Developer Test Company"
DEV_TENANT_SLUG = "developer-test"
DEV_USER_EMAIL = "owner@example.com"
DEV_USER_NAME = "Developer Owner"


def run_migrations() -> None:
    config = Config("alembic.ini")
    command.upgrade(config, "head")


def repair_development_schema() -> None:
    Base.metadata.create_all(bind=engine)

    columns = {
        "users": [("avatar_url", String(255))],
        "companies": [
            ("status", String(40)),
            ("company_type", String(40)),
            ("health_score", Integer()),
            ("client_since", DateTime(timezone=True)),
            ("owner_id", sales_models.Company.owner_id.type),
            ("next_action_id", sales_models.Company.next_action_id.type),
        ],
        "contacts": [
            ("role", String(120)),
            ("can_call", Boolean()),
            ("can_email", Boolean()),
            ("can_open_more", Boolean()),
        ],
        "deals": [
            ("probability", Integer()),
            ("expected_close_date", DateTime(timezone=True)),
            ("expected_next_event", String(255)),
            ("next_step", String(255)),
            ("risk_level", String(40)),
            ("forecast_category", String(40)),
            ("owner_id", sales_models.Deal.owner_id.type),
            ("next_action_id", sales_models.Deal.next_action_id.type),
        ],
        "tasks": [
            ("status", String(40)),
            ("priority", String(40)),
        ],
        "activities": [("channel", String(40))],
    }

    with engine.begin() as connection:
        inspector = inspect(connection)
        for table_name, table_columns in columns.items():
            existing_columns = {item["name"] for item in inspector.get_columns(table_name)}
            for column_name, column_type in table_columns:
                if column_name in existing_columns:
                    continue
                compiled_type = column_type.compile(dialect=connection.dialect)
                connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {compiled_type}"))

        connection.execute(text("UPDATE companies SET status = 'active' WHERE status IS NULL"))
        connection.execute(text("UPDATE companies SET client_since = created_at WHERE client_since IS NULL"))
        connection.execute(text("UPDATE contacts SET can_call = true WHERE can_call IS NULL"))
        connection.execute(text("UPDATE contacts SET can_email = true WHERE can_email IS NULL"))
        connection.execute(text("UPDATE contacts SET can_open_more = true WHERE can_open_more IS NULL"))
        connection.execute(text("UPDATE companies SET health_score = 70 WHERE health_score IS NULL"))
        connection.execute(text("UPDATE tasks SET status = CASE WHEN done_at IS NULL THEN 'open' ELSE 'done' END WHERE status IS NULL"))
        connection.execute(text("UPDATE tasks SET priority = 'normal' WHERE priority IS NULL"))
        connection.execute(text("UPDATE deals SET forecast_category = 'pipeline' WHERE forecast_category IS NULL"))


def ensure_dev_access(db: Session) -> None:
    if not settings.dev_user_password or len(settings.dev_user_password.encode("utf-8")) < 8:
        raise RuntimeError("DEV_USER_PASSWORD must contain at least 8 bytes")
    if len(settings.dev_user_password.encode("utf-8")) > 72:
        raise RuntimeError("DEV_USER_PASSWORD must contain at most 72 bytes")

    tenant = db.query(Tenant).filter(Tenant.slug == DEV_TENANT_SLUG).one_or_none()
    if tenant is None:
        tenant = Tenant(name=DEV_TENANT_NAME, slug=DEV_TENANT_SLUG, is_active=True)
        db.add(tenant)
        db.flush()
    else:
        tenant.name = DEV_TENANT_NAME
        tenant.is_active = True

    user = db.query(User).filter(User.email == DEV_USER_EMAIL).one_or_none()
    password_hash = hash_password(settings.dev_user_password)
    if user is None:
        user = User(
            email=DEV_USER_EMAIL,
            full_name=DEV_USER_NAME,
            avatar_url="/avatars/developer-owner.png",
            password_hash=password_hash,
            is_active=True,
        )
        db.add(user)
        db.flush()
    else:
        user.full_name = DEV_USER_NAME
        user.avatar_url = user.avatar_url or "/avatars/developer-owner.png"
        user.password_hash = password_hash
        user.is_active = True

    membership = (
        db.query(Membership)
        .filter(Membership.tenant_id == tenant.id, Membership.user_id == user.id)
        .one_or_none()
    )
    if membership is None:
        db.add(Membership(tenant_id=tenant.id, user_id=user.id, role="owner", is_active=True))
    else:
        membership.role = "owner"
        membership.is_active = True
        membership.deactivated_at = None
        membership.deactivated_by_id = None

    db.commit()


def main() -> None:
    run_migrations()
    repair_development_schema()
    db = SessionLocal()
    try:
        ensure_dev_access(db)
    finally:
        db.close()

    print("Developer access ready")
    print(f"Tenant slug: {DEV_TENANT_SLUG}")
    print(f"Login: {DEV_USER_EMAIL}")
    print("Password: configured via DEV_USER_PASSWORD")


if __name__ == "__main__":
    main()
