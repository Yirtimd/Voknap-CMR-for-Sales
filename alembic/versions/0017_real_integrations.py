"""add real integrations platform

Revision ID: 0017_real_integrations
Revises: 0016_automation_engine
Create Date: 2026-07-24
"""

from alembic import op
import sqlalchemy as sa


revision = "0017_real_integrations"
down_revision = "0016_automation_engine"
branch_labels = None
depends_on = None


TENANT_TABLES = ("integration_jobs", "webhook_endpoints", "public_api_keys")


def upgrade() -> None:
    op.alter_column(
        "connector_accounts",
        "sync_cursor",
        existing_type=sa.String(length=255),
        type_=sa.Text(),
        existing_nullable=True,
    )

    op.create_table(
        "integration_jobs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("account_id", sa.UUID()),
        sa.Column("job_type", sa.String(80), nullable=False),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("locked_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("result_json", sa.Text(), nullable=False),
        sa.Column("last_error", sa.Text()),
        sa.Column("error_log_json", sa.Text(), nullable=False),
        sa.Column("created_by_id", sa.UUID()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'retry', 'succeeded', 'dead')",
            name="ck_integration_jobs_status",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_integration_jobs_tenant"
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "account_id"],
            ["connector_accounts.tenant_id", "connector_accounts.id"],
            name="fk_integration_jobs_tenant_account_id",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "created_by_id"],
            ["memberships.tenant_id", "memberships.user_id"],
            name="fk_integration_jobs_tenant_created_by_id",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "id", name="uq_integration_jobs_tenant_id"),
        sa.UniqueConstraint(
            "tenant_id",
            "idempotency_key",
            name="uq_integration_jobs_tenant_idempotency",
        ),
    )

    op.create_table(
        "webhook_endpoints",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("event_types_json", sa.Text(), nullable=False),
        sa.Column("secret_encrypted", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_webhook_endpoints_tenant"
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "created_by_id"],
            ["memberships.tenant_id", "memberships.user_id"],
            name="fk_webhook_endpoints_tenant_created_by_id",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "id", name="uq_webhook_endpoints_tenant_id"),
    )

    op.create_table(
        "public_api_keys",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("key_prefix", sa.String(24), nullable=False),
        sa.Column("key_hash", sa.String(64), nullable=False),
        sa.Column("scopes_json", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
        sa.Column("created_by_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_public_api_keys_tenant"
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "created_by_id"],
            ["memberships.tenant_id", "memberships.user_id"],
            name="fk_public_api_keys_tenant_created_by_id",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key_hash", name="uq_public_api_keys_hash"),
        sa.UniqueConstraint("tenant_id", "id", name="uq_public_api_keys_tenant_id"),
    )

    indexes = {
        "integration_jobs": (
            "tenant_id",
            "account_id",
            "job_type",
            "status",
            "available_at",
            "created_by_id",
        ),
        "webhook_endpoints": ("tenant_id", "created_by_id"),
        "public_api_keys": ("tenant_id", "key_prefix", "created_by_id"),
    }
    for table, columns in indexes.items():
        for column in columns:
            op.create_index(op.f(f"ix_{table}_{column}"), table, [column])

    if op.get_bind().dialect.name == "postgresql":
        predicate = "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"
        for table in TENANT_TABLES:
            op.execute(sa.text(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY'))
            op.execute(sa.text(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY'))
            op.execute(
                sa.text(
                    f'CREATE POLICY tenant_isolation ON "{table}" '
                    f"USING ({predicate}) WITH CHECK ({predicate})"
                )
            )
            op.execute(
                sa.text(
                    f'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE "{table}" TO cmr_app'
                )
            )


def downgrade() -> None:
    for table in reversed(TENANT_TABLES):
        op.drop_table(table)
    op.alter_column(
        "connector_accounts",
        "sync_cursor",
        existing_type=sa.Text(),
        type_=sa.String(length=255),
        existing_nullable=True,
    )
