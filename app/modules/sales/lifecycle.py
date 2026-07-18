import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from app.core.dependencies import CurrentTenant
from app.core.rbac import Permission, has_permission, require_allowed_fields, require_object_owner
from app.modules.accounts.models import Membership
from app.modules.sales.models import Contact, Deal, FieldChange, Lead, Note, Task


EntityType = Literal["contacts", "leads", "deals", "tasks", "notes"]
ENTITY_MODELS = {
    "contacts": Contact,
    "leads": Lead,
    "deals": Deal,
    "tasks": Task,
    "notes": Note,
}
OWNER_FIELDS = {
    "contacts": "owner_id",
    "leads": "owner_id",
    "deals": "owner_id",
    "tasks": "assigned_to_id",
    "notes": "author_id",
}
RESTRICTED_FIELDS = {
    "contacts": {"owner_id"},
    "leads": {"owner_id"},
    "deals": {"owner_id", "probability", "risk_level", "forecast_category"},
    "tasks": {"assigned_to_id"},
    "notes": {"author_id"},
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def get_entity(
    db: Session,
    tenant_id: UUID,
    entity_type: EntityType,
    entity_id: UUID,
    *,
    include_deleted: bool = False,
    include_archived: bool = False,
):
    model = ENTITY_MODELS[entity_type]
    query = db.query(model).filter(model.id == entity_id, model.tenant_id == tenant_id)
    if include_deleted or include_archived:
        query = query.execution_options(
            include_deleted=include_deleted,
            include_archived=include_archived,
        )
    if not include_deleted:
        query = query.filter(model.deleted_at.is_(None))
    if not include_archived:
        query = query.filter(model.is_archived.is_(False))
    entity = query.one_or_none()
    if entity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{model.__name__} not found")
    return entity


def require_entity_write_access(
    tenant: CurrentTenant,
    entity_type: EntityType,
    entity: Any,
) -> None:
    require_object_owner(
        tenant.role,
        tenant.user_id,
        getattr(entity, OWNER_FIELDS[entity_type]),
    )


def require_version(entity: Any, expected_version: int) -> None:
    if entity.version != expected_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "Version conflict", "current_version": entity.version},
        )


def ensure_member(db: Session, tenant_id: UUID, user_id: UUID) -> None:
    exists = (
        db.query(Membership.id)
        .filter(Membership.tenant_id == tenant_id, Membership.user_id == user_id)
        .first()
    )
    if exists is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Owner is not a tenant member")


def apply_update(
    db: Session,
    tenant: CurrentTenant,
    entity_type: EntityType,
    entity: Any,
    update_data: dict[str, Any],
) -> list[str]:
    restricted = RESTRICTED_FIELDS[entity_type]
    require_allowed_fields(tenant.role, set(update_data), restricted)
    if OWNER_FIELDS[entity_type] in update_data and update_data[OWNER_FIELDS[entity_type]] is not None:
        ensure_member(db, tenant.id, update_data[OWNER_FIELDS[entity_type]])

    changed_fields = []
    next_version = entity.version + 1
    for field_name, new_value in update_data.items():
        old_value = getattr(entity, field_name)
        if old_value == new_value:
            continue
        setattr(entity, field_name, new_value)
        add_history(
            db,
            tenant,
            entity_type,
            entity.id,
            field_name,
            old_value,
            new_value,
            next_version,
        )
        changed_fields.append(field_name)
    return changed_fields


def set_archived(
    db: Session,
    tenant: CurrentTenant,
    entity_type: EntityType,
    entity: Any,
    is_archived: bool,
) -> None:
    if entity.is_archived == is_archived:
        return
    add_history(
        db,
        tenant,
        entity_type,
        entity.id,
        "is_archived",
        entity.is_archived,
        is_archived,
        entity.version + 1,
    )
    entity.is_archived = is_archived


def soft_delete(
    db: Session,
    tenant: CurrentTenant,
    entity_type: EntityType,
    entity: Any,
) -> None:
    if entity.deleted_at is not None:
        return
    deleted_at = utc_now()
    add_history(
        db,
        tenant,
        entity_type,
        entity.id,
        "deleted_at",
        None,
        deleted_at,
        entity.version + 1,
    )
    entity.deleted_at = deleted_at
    entity.deleted_by_id = tenant.user_id


def restore_deleted(
    db: Session,
    tenant: CurrentTenant,
    entity_type: EntityType,
    entity: Any,
) -> None:
    if entity.deleted_at is None:
        return
    add_history(
        db,
        tenant,
        entity_type,
        entity.id,
        "deleted_at",
        entity.deleted_at,
        None,
        entity.version + 1,
    )
    entity.deleted_at = None
    entity.deleted_by_id = None


def add_history(
    db: Session,
    tenant: CurrentTenant,
    entity_type: EntityType,
    entity_id: UUID,
    field_name: str,
    old_value: Any,
    new_value: Any,
    entity_version: int,
) -> None:
    db.add(
        FieldChange(
            tenant_id=tenant.id,
            entity_type=entity_type,
            entity_id=entity_id,
            field_name=field_name,
            old_value_json=_json_value(old_value),
            new_value_json=_json_value(new_value),
            changed_by_id=tenant.user_id,
            entity_version=entity_version,
        )
    )


def commit_versioned(db: Session, entity: Any) -> None:
    try:
        db.commit()
        db.refresh(entity)
    except StaleDataError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Object was changed by another request",
        ) from error


def can_include_deleted(tenant: CurrentTenant) -> bool:
    return has_permission(tenant.role, Permission.SALES_MANAGE)


def _json_value(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=_json_default)


def _json_default(value: Any) -> str | float:
    if isinstance(value, (datetime, UUID)):
        return str(value)
    if isinstance(value, Decimal):
        return float(value)
    return str(value)
