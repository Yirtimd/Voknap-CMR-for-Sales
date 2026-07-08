"""communication hub

Revision ID: 0006_communication_hub
Revises: 0005_connectors_production_layer
Create Date: 2026-07-08
"""

from alembic import op
import sqlalchemy as sa


revision = "0006_communication_hub"
down_revision = "0005_connectors_production_layer"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = sa.inspect(bind).get_table_names()
    if "communication_events" in tables:
        return

    op.create_table(
        "communication_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=True),
        sa.Column("contact_id", sa.Uuid(), nullable=True),
        sa.Column("deal_id", sa.Uuid(), nullable=True),
        sa.Column("activity_id", sa.Uuid(), nullable=True),
        sa.Column("connector_account_id", sa.Uuid(), nullable=True),
        sa.Column("channel", sa.String(length=40), nullable=False),
        sa.Column("direction", sa.String(length=20), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=True),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("sender", sa.String(length=255), nullable=True),
        sa.Column("recipient", sa.String(length=255), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("ai_summary", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["activity_id"], ["activities.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["connector_account_id"], ["connector_accounts.id"]),
        sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"]),
        sa.ForeignKeyConstraint(["deal_id"], ["deals.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "channel", "external_id", name="uq_communication_event_external"),
    )
    for column_name in (
        "tenant_id",
        "company_id",
        "contact_id",
        "deal_id",
        "activity_id",
        "connector_account_id",
        "channel",
        "direction",
        "status",
        "external_id",
        "occurred_at",
        "created_by",
        "created_at",
    ):
        op.create_index(f"ix_communication_events_{column_name}", "communication_events", [column_name])


def downgrade() -> None:
    bind = op.get_bind()
    tables = sa.inspect(bind).get_table_names()
    if "communication_events" not in tables:
        return
    op.drop_table("communication_events")
