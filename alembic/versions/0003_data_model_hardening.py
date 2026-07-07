"""data model hardening

Revision ID: 0003_data_model_hardening
Revises: 0002_company_workspace_contract
Create Date: 2026-07-07
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_data_model_hardening"
down_revision = "0002_company_workspace_contract"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    existing_tables = set(inspector.get_table_names())
    if "next_actions" not in existing_tables:
        op.create_table(
            "next_actions",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("tenant_id", sa.UUID(), nullable=False),
            sa.Column("company_id", sa.UUID(), nullable=False),
            sa.Column("deal_id", sa.UUID(), nullable=True),
            sa.Column("contact_id", sa.UUID(), nullable=True),
            sa.Column("assigned_to_id", sa.UUID(), nullable=True),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("source", sa.String(length=40), nullable=False),
            sa.Column("status", sa.String(length=40), nullable=False),
            sa.Column("priority", sa.String(length=40), nullable=False),
            sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["assigned_to_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
            sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"]),
            sa.ForeignKeyConstraint(["deal_id"], ["deals.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_next_actions_tenant_id"), "next_actions", ["tenant_id"])
        op.create_index(op.f("ix_next_actions_company_id"), "next_actions", ["company_id"])
        op.create_index(op.f("ix_next_actions_deal_id"), "next_actions", ["deal_id"])
        op.create_index(op.f("ix_next_actions_contact_id"), "next_actions", ["contact_id"])
        op.create_index(op.f("ix_next_actions_assigned_to_id"), "next_actions", ["assigned_to_id"])
        op.create_index(op.f("ix_next_actions_status"), "next_actions", ["status"])

    _add_column_if_missing("companies", "health_score", sa.Column("health_score", sa.Integer(), nullable=True))
    _add_column_if_missing("companies", "next_action_id", sa.Column("next_action_id", sa.UUID(), nullable=True))

    _add_column_if_missing("deals", "expected_close_date", sa.Column("expected_close_date", sa.DateTime(timezone=True), nullable=True))
    _add_column_if_missing("deals", "risk_level", sa.Column("risk_level", sa.String(length=40), nullable=True))
    _add_column_if_missing("deals", "forecast_category", sa.Column("forecast_category", sa.String(length=40), nullable=True))
    _add_column_if_missing("deals", "next_action_id", sa.Column("next_action_id", sa.UUID(), nullable=True))

    _add_column_if_missing("tasks", "status", sa.Column("status", sa.String(length=40), nullable=True))
    _add_column_if_missing("tasks", "priority", sa.Column("priority", sa.String(length=40), nullable=True))

    _create_fk_if_missing("companies", "fk_companies_next_action_id_next_actions", ["next_action_id"], "next_actions", ["id"])
    _create_fk_if_missing("deals", "fk_deals_next_action_id_next_actions", ["next_action_id"], "next_actions", ["id"])

    op.execute("UPDATE companies SET health_score = 70 WHERE health_score IS NULL")
    op.execute("UPDATE tasks SET status = CASE WHEN done_at IS NULL THEN 'open' ELSE 'done' END WHERE status IS NULL")
    op.execute("UPDATE tasks SET priority = 'normal' WHERE priority IS NULL")
    op.execute("UPDATE deals SET forecast_category = 'pipeline' WHERE forecast_category IS NULL")


def downgrade() -> None:
    _drop_fk_if_present("deals", "fk_deals_next_action_id_next_actions")
    _drop_fk_if_present("companies", "fk_companies_next_action_id_next_actions")
    _drop_columns_if_present("tasks", ["priority", "status"])
    _drop_columns_if_present("deals", ["next_action_id", "forecast_category", "risk_level", "expected_close_date"])
    _drop_columns_if_present("companies", ["next_action_id", "health_score"])

    bind = op.get_bind()
    if "next_actions" in set(sa.inspect(bind).get_table_names()):
        op.drop_index(op.f("ix_next_actions_status"), table_name="next_actions")
        op.drop_index(op.f("ix_next_actions_assigned_to_id"), table_name="next_actions")
        op.drop_index(op.f("ix_next_actions_contact_id"), table_name="next_actions")
        op.drop_index(op.f("ix_next_actions_deal_id"), table_name="next_actions")
        op.drop_index(op.f("ix_next_actions_company_id"), table_name="next_actions")
        op.drop_index(op.f("ix_next_actions_tenant_id"), table_name="next_actions")
        op.drop_table("next_actions")


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


def _create_fk_if_missing(
    table_name: str,
    constraint_name: str,
    local_cols: list[str],
    remote_table: str,
    remote_cols: list[str],
) -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return
    constraints = {item["name"] for item in sa.inspect(bind).get_foreign_keys(table_name)}
    if constraint_name not in constraints:
        op.create_foreign_key(constraint_name, table_name, remote_table, local_cols, remote_cols)


def _drop_fk_if_present(table_name: str, constraint_name: str) -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return
    constraints = {item["name"] for item in sa.inspect(bind).get_foreign_keys(table_name)}
    if constraint_name in constraints:
        op.drop_constraint(constraint_name, table_name, type_="foreignkey")
