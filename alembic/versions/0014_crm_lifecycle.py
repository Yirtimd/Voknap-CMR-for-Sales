"""add complete CRM lifecycle contracts

Revision ID: 0014_crm_lifecycle
Revises: 0013_membership_roles
Create Date: 2026-07-18
"""

from alembic import op
import sqlalchemy as sa


revision = "0014_crm_lifecycle"
down_revision = "0013_membership_roles"
branch_labels = None
depends_on = None


LIFECYCLE_TABLES = ("contacts", "leads", "deals", "tasks", "notes")
MEMBERSHIP_COLUMNS = (
    ("contacts", "owner_id"),
    ("contacts", "deleted_by_id"),
    ("leads", "owner_id"),
    ("leads", "qualified_by_id"),
    ("leads", "converted_by_id"),
    ("leads", "deleted_by_id"),
    ("deals", "deleted_by_id"),
    ("tasks", "deleted_by_id"),
    ("notes", "deleted_by_id"),
)


def upgrade() -> None:
    for table in LIFECYCLE_TABLES:
        if table in {"contacts", "leads"}:
            op.add_column(table, sa.Column("owner_id", sa.UUID(), nullable=True))
            op.create_foreign_key(None, table, "users", ["owner_id"], ["id"])
            op.create_index(op.f(f"ix_{table}_owner_id"), table, ["owner_id"])
        op.add_column(
            table,
            sa.Column("is_archived", sa.Boolean(), server_default=sa.false(), nullable=False),
        )
        op.add_column(table, sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
        op.add_column(table, sa.Column("deleted_by_id", sa.UUID(), nullable=True))
        op.add_column(table, sa.Column("version", sa.Integer(), server_default="1", nullable=False))
        op.add_column(table, sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))
        op.execute(sa.text(f'UPDATE "{table}" SET updated_at = created_at WHERE updated_at IS NULL'))
        op.alter_column(table, "updated_at", nullable=False)
        op.create_foreign_key(None, table, "users", ["deleted_by_id"], ["id"])
        op.create_index(op.f(f"ix_{table}_is_archived"), table, ["is_archived"])
        op.create_index(op.f(f"ix_{table}_deleted_at"), table, ["deleted_at"])

    op.execute(
        "UPDATE contacts SET owner_id = companies.owner_id "
        "FROM companies WHERE contacts.company_id = companies.id "
        "AND contacts.tenant_id = companies.tenant_id"
    )
    op.execute(
        "UPDATE leads SET owner_id = companies.owner_id "
        "FROM companies WHERE leads.company_id = companies.id "
        "AND leads.tenant_id = companies.tenant_id"
    )

    op.add_column("leads", sa.Column("qualified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("leads", sa.Column("qualified_by_id", sa.UUID(), nullable=True))
    op.add_column("leads", sa.Column("converted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("leads", sa.Column("converted_by_id", sa.UUID(), nullable=True))
    op.add_column("leads", sa.Column("converted_deal_id", sa.UUID(), nullable=True))
    op.add_column("leads", sa.Column("disqualification_reason", sa.Text(), nullable=True))
    op.create_foreign_key(None, "leads", "users", ["qualified_by_id"], ["id"])
    op.create_foreign_key(None, "leads", "users", ["converted_by_id"], ["id"])
    op.create_foreign_key(
        "fk_leads_converted_deal_id_deals",
        "leads",
        "deals",
        ["converted_deal_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_leads_tenant_converted_deal_id",
        "leads",
        "deals",
        ["tenant_id", "converted_deal_id"],
        ["tenant_id", "id"],
    )

    for table, column in MEMBERSHIP_COLUMNS:
        op.create_foreign_key(
            f"fk_{table}_tenant_{column}",
            table,
            "memberships",
            ["tenant_id", column],
            ["tenant_id", "user_id"],
        )

    op.create_table(
        "crm_field_changes",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("entity_type", sa.String(length=40), nullable=False),
        sa.Column("entity_id", sa.UUID(), nullable=False),
        sa.Column("field_name", sa.String(length=80), nullable=False),
        sa.Column("old_value_json", sa.Text(), nullable=True),
        sa.Column("new_value_json", sa.Text(), nullable=True),
        sa.Column("changed_by_id", sa.UUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("entity_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_crm_field_changes_tenant"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "changed_by_id"],
            ["memberships.tenant_id", "memberships.user_id"],
            name="fk_crm_field_changes_tenant_changed_by_id",
        ),
        sa.UniqueConstraint("tenant_id", "id", name="uq_crm_field_changes_tenant_id"),
    )
    op.create_index(op.f("ix_crm_field_changes_tenant_id"), "crm_field_changes", ["tenant_id"])
    op.create_index(op.f("ix_crm_field_changes_entity_type"), "crm_field_changes", ["entity_type"])
    op.create_index(op.f("ix_crm_field_changes_entity_id"), "crm_field_changes", ["entity_id"])

    tenant_predicate = "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"
    op.execute('ALTER TABLE "crm_field_changes" ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE "crm_field_changes" FORCE ROW LEVEL SECURITY')
    op.execute(
        'CREATE POLICY tenant_isolation ON "crm_field_changes" '
        f"USING ({tenant_predicate}) WITH CHECK ({tenant_predicate})"
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE crm_field_changes TO cmr_app"
    )


def downgrade() -> None:
    op.execute('DROP POLICY IF EXISTS tenant_isolation ON "crm_field_changes"')
    op.drop_table("crm_field_changes")

    for table, column in reversed(MEMBERSHIP_COLUMNS):
        op.drop_constraint(f"fk_{table}_tenant_{column}", table, type_="foreignkey")
    op.drop_constraint("fk_leads_tenant_converted_deal_id", "leads", type_="foreignkey")
    op.drop_constraint("fk_leads_converted_deal_id_deals", "leads", type_="foreignkey")
    for column in (
        "disqualification_reason",
        "converted_deal_id",
        "converted_by_id",
        "converted_at",
        "qualified_by_id",
        "qualified_at",
    ):
        op.drop_column("leads", column)

    for table in reversed(LIFECYCLE_TABLES):
        for column in ("updated_at", "version", "deleted_by_id", "deleted_at", "is_archived"):
            op.drop_column(table, column)
        if table in {"contacts", "leads"}:
            op.drop_column(table, "owner_id")
