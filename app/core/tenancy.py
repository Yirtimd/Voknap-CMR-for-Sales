from collections.abc import Iterable

from sqlalchemy import ForeignKeyConstraint, UniqueConstraint


def tenant_table_args(
    table: str,
    *,
    relations: Iterable[tuple[str, str]] = (),
    membership_columns: Iterable[str] = (),
    extra: Iterable[object] = (),
) -> tuple[object, ...]:
    constraints: list[object] = [
        UniqueConstraint("tenant_id", "id", name=f"uq_{table}_tenant_id"),
        ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=f"fk_{table}_tenant",
        ),
    ]
    constraints.extend(
        ForeignKeyConstraint(
            ["tenant_id", column],
            [f"{target}.tenant_id", f"{target}.id"],
            name=f"fk_{table}_tenant_{column}",
        )
        for column, target in relations
    )
    constraints.extend(
        ForeignKeyConstraint(
            ["tenant_id", column],
            ["memberships.tenant_id", "memberships.user_id"],
            name=f"fk_{table}_tenant_{column}",
        )
        for column in membership_columns
    )
    constraints.extend(extra)
    return tuple(constraints)
