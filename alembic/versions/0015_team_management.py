"""add team management and assignment routing

Revision ID: 0015_team_management
Revises: 0014_crm_lifecycle
Create Date: 2026-07-19
"""

from alembic import op
import sqlalchemy as sa


revision = "0015_team_management"
down_revision = "0014_crm_lifecycle"
branch_labels = None
depends_on = None


TENANT_TABLES = (
    "sales_teams",
    "team_invitations",
    "lead_queues",
    "lead_queue_members",
    "territories",
    "assignment_rules",
)


def upgrade() -> None:
    op.create_unique_constraint("uq_memberships_tenant_id", "memberships", ["tenant_id", "id"])
    op.add_column(
        "memberships",
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.add_column("memberships", sa.Column("team_id", sa.UUID(), nullable=True))
    op.add_column("memberships", sa.Column("manager_membership_id", sa.UUID(), nullable=True))
    op.add_column("memberships", sa.Column("deactivated_at", sa.DateTime(timezone=True)))
    op.add_column("memberships", sa.Column("deactivated_by_id", sa.UUID()))
    op.create_foreign_key(None, "memberships", "users", ["deactivated_by_id"], ["id"])
    op.create_index(op.f("ix_memberships_is_active"), "memberships", ["is_active"])
    op.create_index(op.f("ix_memberships_team_id"), "memberships", ["team_id"])
    op.create_index(
        op.f("ix_memberships_manager_membership_id"),
        "memberships",
        ["manager_membership_id"],
    )

    op.create_table(
        "sales_teams",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("manager_membership_id", sa.UUID()),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_sales_teams_tenant"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "manager_membership_id"],
            ["memberships.tenant_id", "memberships.id"],
            name="fk_sales_teams_tenant_manager_membership_id",
            use_alter=True,
        ),
        sa.UniqueConstraint("tenant_id", "id", name="uq_sales_teams_tenant_id"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_sales_teams_tenant_name"),
    )
    op.create_index(op.f("ix_sales_teams_tenant_id"), "sales_teams", ["tenant_id"])
    op.create_index(
        op.f("ix_sales_teams_manager_membership_id"),
        "sales_teams",
        ["manager_membership_id"],
    )

    op.create_foreign_key(
        "fk_memberships_tenant_team_id",
        "memberships",
        "sales_teams",
        ["tenant_id", "team_id"],
        ["tenant_id", "id"],
        use_alter=True,
    )
    op.create_foreign_key(
        "fk_memberships_tenant_manager_membership_id",
        "memberships",
        "memberships",
        ["tenant_id", "manager_membership_id"],
        ["tenant_id", "id"],
        use_alter=True,
    )
    op.create_foreign_key(
        "fk_memberships_tenant_deactivated_by_id",
        "memberships",
        "memberships",
        ["tenant_id", "deactivated_by_id"],
        ["tenant_id", "user_id"],
        use_alter=True,
    )
    op.create_foreign_key(
        "fk_sales_teams_tenant_manager_membership_id",
        "sales_teams",
        "memberships",
        ["tenant_id", "manager_membership_id"],
        ["tenant_id", "id"],
        use_alter=True,
    )

    op.create_table(
        "team_invitations",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("role", sa.String(40), nullable=False),
        sa.Column("team_id", sa.UUID()),
        sa.Column("manager_membership_id", sa.UUID()),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("invited_by_id", sa.UUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "role IN ('owner', 'admin', 'sales_manager', 'sales_rep', 'viewer')",
            name="ck_team_invitations_role",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_team_invitations_tenant"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "team_id"],
            ["sales_teams.tenant_id", "sales_teams.id"],
            name="fk_team_invitations_tenant_team_id",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "manager_membership_id"],
            ["memberships.tenant_id", "memberships.id"],
            name="fk_team_invitations_tenant_manager_membership_id",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "invited_by_id"],
            ["memberships.tenant_id", "memberships.user_id"],
            name="fk_team_invitations_tenant_invited_by_id",
        ),
        sa.UniqueConstraint("tenant_id", "id", name="uq_team_invitations_tenant_id"),
        sa.UniqueConstraint("token_hash", name="uq_team_invitations_token_hash"),
    )
    for column in ("tenant_id", "email", "team_id", "manager_membership_id"):
        op.create_index(op.f(f"ix_team_invitations_{column}"), "team_invitations", [column])

    op.create_table(
        "lead_queues",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("team_id", sa.UUID()),
        sa.Column("strategy", sa.String(40), server_default="round_robin", nullable=False),
        sa.Column("routing_cursor", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_lead_queues_tenant"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "team_id"],
            ["sales_teams.tenant_id", "sales_teams.id"],
            name="fk_lead_queues_tenant_team_id",
        ),
        sa.UniqueConstraint("tenant_id", "id", name="uq_lead_queues_tenant_id"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_lead_queues_tenant_name"),
    )
    op.create_index(op.f("ix_lead_queues_tenant_id"), "lead_queues", ["tenant_id"])
    op.create_index(op.f("ix_lead_queues_team_id"), "lead_queues", ["team_id"])

    op.create_table(
        "lead_queue_members",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("queue_id", sa.UUID(), nullable=False),
        sa.Column("membership_id", sa.UUID(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_lead_queue_members_tenant"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "queue_id"],
            ["lead_queues.tenant_id", "lead_queues.id"],
            name="fk_lead_queue_members_tenant_queue_id",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "membership_id"],
            ["memberships.tenant_id", "memberships.id"],
            name="fk_lead_queue_members_tenant_membership_id",
        ),
        sa.UniqueConstraint("tenant_id", "id", name="uq_lead_queue_members_tenant_id"),
        sa.UniqueConstraint(
            "tenant_id", "queue_id", "membership_id", name="uq_lead_queue_members_member"
        ),
    )
    for column in ("tenant_id", "queue_id", "membership_id"):
        op.create_index(op.f(f"ix_lead_queue_members_{column}"), "lead_queue_members", [column])

    op.create_table(
        "territories",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("country_code", sa.String(2)),
        sa.Column("region", sa.String(120)),
        sa.Column("industry", sa.String(120)),
        sa.Column("owner_membership_id", sa.UUID()),
        sa.Column("team_id", sa.UUID()),
        sa.Column("priority", sa.Integer(), server_default="100", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_territories_tenant"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "owner_membership_id"],
            ["memberships.tenant_id", "memberships.id"],
            name="fk_territories_tenant_owner_membership_id",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "team_id"],
            ["sales_teams.tenant_id", "sales_teams.id"],
            name="fk_territories_tenant_team_id",
        ),
        sa.UniqueConstraint("tenant_id", "id", name="uq_territories_tenant_id"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_territories_tenant_name"),
    )
    for column in ("tenant_id", "owner_membership_id", "team_id"):
        op.create_index(op.f(f"ix_territories_{column}"), "territories", [column])

    op.create_table(
        "assignment_rules",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("entity_type", sa.String(20), nullable=False),
        sa.Column("criteria_json", sa.Text(), server_default="{}", nullable=False),
        sa.Column("target_type", sa.String(20), nullable=False),
        sa.Column("assignee_id", sa.UUID()),
        sa.Column("team_id", sa.UUID()),
        sa.Column("queue_id", sa.UUID()),
        sa.Column("territory_id", sa.UUID()),
        sa.Column("priority", sa.Integer(), server_default="100", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("entity_type IN ('lead', 'company')", name="ck_assignment_rules_entity"),
        sa.CheckConstraint(
            "target_type IN ('member', 'team', 'queue', 'territory')",
            name="ck_assignment_rules_target",
        ),
        sa.CheckConstraint(
            "(target_type = 'member' AND assignee_id IS NOT NULL AND team_id IS NULL "
            "AND queue_id IS NULL AND territory_id IS NULL) OR "
            "(target_type = 'team' AND assignee_id IS NULL AND team_id IS NOT NULL "
            "AND queue_id IS NULL AND territory_id IS NULL) OR "
            "(target_type = 'queue' AND assignee_id IS NULL AND team_id IS NULL "
            "AND queue_id IS NOT NULL AND territory_id IS NULL) OR "
            "(target_type = 'territory' AND assignee_id IS NULL AND team_id IS NULL "
            "AND queue_id IS NULL AND territory_id IS NOT NULL)",
            name="ck_assignment_rules_target_reference",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_assignment_rules_tenant"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "assignee_id"],
            ["memberships.tenant_id", "memberships.user_id"],
            name="fk_assignment_rules_tenant_assignee_id",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "team_id"],
            ["sales_teams.tenant_id", "sales_teams.id"],
            name="fk_assignment_rules_tenant_team_id",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "queue_id"],
            ["lead_queues.tenant_id", "lead_queues.id"],
            name="fk_assignment_rules_tenant_queue_id",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "territory_id"],
            ["territories.tenant_id", "territories.id"],
            name="fk_assignment_rules_tenant_territory_id",
        ),
        sa.UniqueConstraint("tenant_id", "id", name="uq_assignment_rules_tenant_id"),
    )
    for column in (
        "tenant_id",
        "entity_type",
        "assignee_id",
        "team_id",
        "queue_id",
        "territory_id",
    ):
        op.create_index(op.f(f"ix_assignment_rules_{column}"), "assignment_rules", [column])

    op.add_column("companies", sa.Column("country_code", sa.String(2)))
    op.add_column("companies", sa.Column("region", sa.String(120)))
    op.add_column("companies", sa.Column("territory_id", sa.UUID()))
    op.create_index(op.f("ix_companies_territory_id"), "companies", ["territory_id"])
    op.create_foreign_key(
        "fk_companies_tenant_territory_id",
        "companies",
        "territories",
        ["tenant_id", "territory_id"],
        ["tenant_id", "id"],
    )
    op.add_column("leads", sa.Column("queue_id", sa.UUID()))
    op.create_index(op.f("ix_leads_queue_id"), "leads", ["queue_id"])
    op.create_foreign_key(
        "fk_leads_tenant_queue_id",
        "leads",
        "lead_queues",
        ["tenant_id", "queue_id"],
        ["tenant_id", "id"],
    )

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
            op.execute(sa.text(f'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE "{table}" TO cmr_app'))


def downgrade() -> None:
    op.drop_constraint("fk_leads_tenant_queue_id", "leads", type_="foreignkey")
    op.drop_index(op.f("ix_leads_queue_id"), table_name="leads")
    op.drop_column("leads", "queue_id")
    op.drop_constraint("fk_companies_tenant_territory_id", "companies", type_="foreignkey")
    op.drop_index(op.f("ix_companies_territory_id"), table_name="companies")
    for column in ("territory_id", "region", "country_code"):
        op.drop_column("companies", column)

    op.drop_table("assignment_rules")
    op.drop_table("territories")
    op.drop_table("lead_queue_members")
    op.drop_table("lead_queues")
    op.drop_table("team_invitations")
    op.drop_constraint("fk_memberships_tenant_manager_membership_id", "memberships", type_="foreignkey")
    op.drop_constraint("fk_memberships_tenant_deactivated_by_id", "memberships", type_="foreignkey")
    op.drop_constraint("fk_memberships_tenant_team_id", "memberships", type_="foreignkey")
    op.drop_table("sales_teams")
    for column in (
        "deactivated_by_id",
        "deactivated_at",
        "manager_membership_id",
        "team_id",
        "is_active",
    ):
        op.drop_column("memberships", column)
    op.drop_constraint("uq_memberships_tenant_id", "memberships", type_="unique")
