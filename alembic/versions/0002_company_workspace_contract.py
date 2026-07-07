"""company workspace contract

Revision ID: 0002_company_workspace_contract
Revises: 0001_initial_schema
Create Date: 2026-07-07
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_company_workspace_contract"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    _add_column_if_missing("users", "avatar_url", sa.Column("avatar_url", sa.String(length=255), nullable=True))

    _add_column_if_missing("companies", "status", sa.Column("status", sa.String(length=40), nullable=True))
    _add_column_if_missing("companies", "company_type", sa.Column("company_type", sa.String(length=40), nullable=True))
    _add_column_if_missing("companies", "client_since", sa.Column("client_since", sa.DateTime(timezone=True), nullable=True))
    _add_column_if_missing("companies", "owner_id", sa.Column("owner_id", sa.UUID(), nullable=True))

    _add_column_if_missing("contacts", "role", sa.Column("role", sa.String(length=120), nullable=True))
    _add_column_if_missing("contacts", "can_call", sa.Column("can_call", sa.Boolean(), nullable=True))
    _add_column_if_missing("contacts", "can_email", sa.Column("can_email", sa.Boolean(), nullable=True))
    _add_column_if_missing("contacts", "can_open_more", sa.Column("can_open_more", sa.Boolean(), nullable=True))

    _add_column_if_missing("deals", "probability", sa.Column("probability", sa.Integer(), nullable=True))
    _add_column_if_missing("deals", "expected_next_event", sa.Column("expected_next_event", sa.String(length=255), nullable=True))
    _add_column_if_missing("deals", "next_step", sa.Column("next_step", sa.String(length=255), nullable=True))
    _add_column_if_missing("deals", "owner_id", sa.Column("owner_id", sa.UUID(), nullable=True))

    _add_column_if_missing("activities", "channel", sa.Column("channel", sa.String(length=40), nullable=True))

    existing_tables = set(inspector.get_table_names())
    if "customer_insights" not in existing_tables:
        op.create_table(
            "customer_insights",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("tenant_id", sa.UUID(), nullable=False),
            sa.Column("company_id", sa.UUID(), nullable=False),
            sa.Column("health_score", sa.Integer(), nullable=True),
            sa.Column("health_label", sa.String(length=80), nullable=True),
            sa.Column("health_trend", sa.String(length=20), nullable=True),
            sa.Column("risk_level", sa.String(length=40), nullable=True),
            sa.Column("success_chance", sa.Integer(), nullable=True),
            sa.Column("success_chance_delta", sa.Integer(), nullable=True),
            sa.Column("ai_recommendations_json", sa.Text(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("tenant_id", "company_id", name="uq_customer_insight_tenant_company"),
        )
        op.create_index(op.f("ix_customer_insights_tenant_id"), "customer_insights", ["tenant_id"])
        op.create_index(op.f("ix_customer_insights_company_id"), "customer_insights", ["company_id"])

    if "files" not in existing_tables:
        op.create_table(
            "files",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("tenant_id", sa.UUID(), nullable=False),
            sa.Column("company_id", sa.UUID(), nullable=True),
            sa.Column("deal_id", sa.UUID(), nullable=True),
            sa.Column("contact_id", sa.UUID(), nullable=True),
            sa.Column("activity_id", sa.UUID(), nullable=True),
            sa.Column("uploaded_by_id", sa.UUID(), nullable=True),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("file_type", sa.String(length=40), nullable=True),
            sa.Column("mime_type", sa.String(length=120), nullable=True),
            sa.Column("file_size", sa.Integer(), nullable=True),
            sa.Column("storage_key", sa.String(length=500), nullable=False),
            sa.Column("download_url", sa.String(length=500), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["activity_id"], ["activities.id"]),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
            sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"]),
            sa.ForeignKeyConstraint(["deal_id"], ["deals.id"]),
            sa.ForeignKeyConstraint(["uploaded_by_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_files_tenant_id"), "files", ["tenant_id"])
        op.create_index(op.f("ix_files_company_id"), "files", ["company_id"])
        op.create_index(op.f("ix_files_deal_id"), "files", ["deal_id"])
        op.create_index(op.f("ix_files_contact_id"), "files", ["contact_id"])
        op.create_index(op.f("ix_files_activity_id"), "files", ["activity_id"])

    op.execute("UPDATE companies SET status = 'active' WHERE status IS NULL")
    op.execute("UPDATE companies SET client_since = created_at WHERE client_since IS NULL")
    op.execute("UPDATE contacts SET can_call = true WHERE can_call IS NULL")
    op.execute("UPDATE contacts SET can_email = true WHERE can_email IS NULL")
    op.execute("UPDATE contacts SET can_open_more = true WHERE can_open_more IS NULL")


def downgrade() -> None:
    op.drop_index(op.f("ix_files_activity_id"), table_name="files")
    op.drop_index(op.f("ix_files_contact_id"), table_name="files")
    op.drop_index(op.f("ix_files_deal_id"), table_name="files")
    op.drop_index(op.f("ix_files_company_id"), table_name="files")
    op.drop_index(op.f("ix_files_tenant_id"), table_name="files")
    op.drop_table("files")

    op.drop_index(op.f("ix_customer_insights_company_id"), table_name="customer_insights")
    op.drop_index(op.f("ix_customer_insights_tenant_id"), table_name="customer_insights")
    op.drop_table("customer_insights")

    _drop_columns_if_present("activities", ["channel"])
    _drop_columns_if_present("deals", ["owner_id", "next_step", "expected_next_event", "probability"])
    _drop_columns_if_present("contacts", ["can_open_more", "can_email", "can_call", "role"])
    _drop_columns_if_present("companies", ["owner_id", "client_since", "company_type", "status"])
    _drop_columns_if_present("users", ["avatar_url"])


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
