"""connectors production layer

Revision ID: 0005_connectors_production_layer
Revises: 0004_company_knowledge_scope
Create Date: 2026-07-07
"""

from alembic import op
import sqlalchemy as sa


revision = "0005_connectors_production_layer"
down_revision = "0004_company_knowledge_scope"
branch_labels = None
depends_on = None


def upgrade() -> None:
    _add_column_if_missing("connector_accounts", "credentials_encrypted", sa.Column("credentials_encrypted", sa.Boolean(), nullable=True))
    _add_column_if_missing("connector_accounts", "sync_cursor", sa.Column("sync_cursor", sa.String(length=255), nullable=True))
    _add_column_if_missing("connector_sync_runs", "job_type", sa.Column("job_type", sa.String(length=80), nullable=True))
    _add_column_if_missing("connector_sync_runs", "attempt", sa.Column("attempt", sa.Integer(), nullable=True))
    _add_column_if_missing("connector_sync_runs", "max_attempts", sa.Column("max_attempts", sa.Integer(), nullable=True))
    _add_column_if_missing("connector_sync_runs", "next_retry_at", sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True))
    _add_column_if_missing("connector_sync_runs", "started_at", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
    _add_column_if_missing("connector_sync_runs", "finished_at", sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True))
    _add_column_if_missing("connector_sync_runs", "error_code", sa.Column("error_code", sa.String(length=120), nullable=True))
    _add_column_if_missing("connector_sync_runs", "error_details_json", sa.Column("error_details_json", sa.Text(), nullable=True))

    op.execute("UPDATE connector_accounts SET credentials_encrypted = false WHERE credentials_encrypted IS NULL")
    op.execute("UPDATE connector_sync_runs SET job_type = 'sync' WHERE job_type IS NULL")
    op.execute("UPDATE connector_sync_runs SET attempt = 1 WHERE attempt IS NULL")
    op.execute("UPDATE connector_sync_runs SET max_attempts = 3 WHERE max_attempts IS NULL")
    op.execute("UPDATE connector_sync_runs SET error_details_json = '{}' WHERE error_details_json IS NULL")


def downgrade() -> None:
    _drop_columns_if_present(
        "connector_sync_runs",
        [
            "error_details_json",
            "error_code",
            "finished_at",
            "started_at",
            "next_retry_at",
            "max_attempts",
            "attempt",
            "job_type",
        ],
    )
    _drop_columns_if_present("connector_accounts", ["sync_cursor", "credentials_encrypted"])


def _add_column_if_missing(table_name: str, column_name: str, column: sa.Column) -> None:
    bind = op.get_bind()
    columns = {item["name"] for item in sa.inspect(bind).get_columns(table_name)}
    if column_name not in columns:
        op.add_column(table_name, column)


def _drop_columns_if_present(table_name: str, column_names: list[str]) -> None:
    bind = op.get_bind()
    columns = {item["name"] for item in sa.inspect(bind).get_columns(table_name)}
    present_columns = [column_name for column_name in column_names if column_name in columns]
    if not present_columns:
        return
    with op.batch_alter_table(table_name) as batch_op:
        for column_name in present_columns:
            batch_op.drop_column(column_name)
