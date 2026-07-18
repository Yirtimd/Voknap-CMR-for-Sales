"""align nullable and foreign-key schema contracts

Revision ID: 0012_schema_contract_alignment
Revises: 0011_tenant_rls
Create Date: 2026-07-18
"""

from alembic import op
import sqlalchemy as sa


revision = "0012_schema_contract_alignment"
down_revision = "0011_tenant_rls"
branch_labels = None
depends_on = None


NOT_NULL_COLUMNS = (
    ("communication_events", "direction", sa.String(length=20), "'inbound'"),
    ("communication_events", "status", sa.String(length=40), "'new'"),
    ("communication_events", "metadata_json", sa.Text(), "'{}'"),
    ("companies", "status", sa.String(length=40), "'active'"),
    ("connector_accounts", "credentials_encrypted", sa.Boolean(), "false"),
    ("connector_sync_runs", "job_type", sa.String(length=80), "'sync'"),
    ("connector_sync_runs", "attempt", sa.Integer(), "1"),
    ("connector_sync_runs", "max_attempts", sa.Integer(), "3"),
    ("connector_sync_runs", "error_details_json", sa.Text(), "'{}'"),
    ("contacts", "can_call", sa.Boolean(), "true"),
    ("contacts", "can_email", sa.Boolean(), "true"),
    ("contacts", "can_open_more", sa.Boolean(), "true"),
    ("knowledge_chunks", "scope", sa.String(length=40), "'global'"),
    ("knowledge_documents", "visibility", sa.String(length=40), "'global'"),
    ("knowledge_queries", "scope", sa.String(length=40), "'global'"),
    ("knowledge_queries", "include_global", sa.Boolean(), "false"),
    ("tasks", "status", sa.String(length=40), "'open'"),
    ("tasks", "priority", sa.String(length=40), "'normal'"),
)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(
        "UPDATE tasks SET status = CASE WHEN done_at IS NULL THEN 'open' ELSE 'done' END "
        "WHERE status IS NULL"
    )

    for table, column, existing_type, fallback in NOT_NULL_COLUMNS:
        if not (table == "tasks" and column == "status"):
            op.execute(
                sa.text(
                    f'UPDATE "{table}" SET "{column}" = {fallback} '
                    f'WHERE "{column}" IS NULL'
                )
            )
        op.alter_column(
            table,
            column,
            existing_type=existing_type,
            nullable=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    for table, column, existing_type, _fallback in reversed(NOT_NULL_COLUMNS):
        op.alter_column(
            table,
            column,
            existing_type=existing_type,
            nullable=True,
        )

