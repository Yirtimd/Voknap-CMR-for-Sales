from typing import Any

from fastapi import HTTPException, Response, status
from sqlalchemy import asc, desc, or_
from sqlalchemy.orm import Query


def apply_list_contract(
    query: Query,
    model: Any,
    response: Response,
    *,
    search: str | None,
    search_fields: tuple[str, ...],
    filters: dict[str, Any],
    include_archived: bool,
    include_deleted: bool,
    page: int,
    page_size: int,
    sort: str,
    order: str,
    sortable_fields: set[str],
) -> list[Any]:
    query = query.execution_options(
        include_deleted=include_deleted,
        include_archived=include_archived,
    )
    if not include_deleted:
        query = query.filter(model.deleted_at.is_(None))
    if not include_archived:
        query = query.filter(model.is_archived.is_(False))
    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(*(getattr(model, field).ilike(pattern) for field in search_fields))
        )
    for field_name, value in filters.items():
        if value is not None:
            query = query.filter(getattr(model, field_name) == value)
    if sort not in sortable_fields:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported sort field: {sort}",
        )
    sort_column = getattr(model, sort)
    direction = desc if order == "desc" else asc
    total = query.order_by(None).count()
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Page"] = str(page)
    response.headers["X-Page-Size"] = str(page_size)
    response.headers["X-Total-Pages"] = str((total + page_size - 1) // page_size)
    return (
        query.order_by(direction(sort_column), model.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
