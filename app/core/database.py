from collections.abc import Generator
import re
from uuid import UUID

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker, with_loader_criteria

from app.core.config import settings


connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
_ROLE_PATTERN = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")


class Base(DeclarativeBase):
    pass


@event.listens_for(Session, "after_begin")
def _apply_request_rls_context(session: Session, _transaction, connection) -> None:
    if not session.info.get("enforce_tenant_rls"):
        return
    if connection.dialect.name != "postgresql":
        return

    role = settings.database_runtime_role
    if not _ROLE_PATTERN.fullmatch(role):
        raise RuntimeError("DATABASE_RUNTIME_ROLE must be a valid PostgreSQL identifier")

    connection.exec_driver_sql(f'SET LOCAL ROLE "{role}"')
    tenant_id = session.info.get("tenant_id")
    if tenant_id:
        connection.execute(
            text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
            {"tenant_id": str(tenant_id)},
        )


@event.listens_for(Session, "do_orm_execute")
def _hide_soft_deleted_rows(execute_state) -> None:
    if not execute_state.is_select:
        return
    from app.modules.sales.models import Contact, Deal, Lead, Note, Task

    statement = execute_state.statement
    for model in (Contact, Lead, Deal, Task, Note):
        if not execute_state.execution_options.get("include_deleted"):
            statement = statement.options(
                with_loader_criteria(
                    model,
                    lambda entity: entity.deleted_at.is_(None),
                    include_aliases=True,
                )
            )
        if not execute_state.execution_options.get("include_archived"):
            statement = statement.options(
                with_loader_criteria(
                    model,
                    lambda entity: entity.is_archived.is_(False),
                    include_aliases=True,
                )
            )
    execute_state.statement = statement


def set_tenant_context(db: Session, tenant_id: UUID) -> None:
    db.info["tenant_id"] = tenant_id
    if db.get_bind().dialect.name == "postgresql":
        db.execute(
            text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
            {"tenant_id": str(tenant_id)},
        )


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    db.info["enforce_tenant_rls"] = True
    try:
        yield db
    finally:
        db.close()
