"""add automation engine

Revision ID: 0016_automation_engine
Revises: 0015_team_management
Create Date: 2026-07-19
"""

from alembic import op
import sqlalchemy as sa


revision = "0016_automation_engine"
down_revision = "0015_team_management"
branch_labels = None
depends_on = None


TENANT_TABLES = (
    "message_templates",
    "automation_workflows",
    "automation_runs",
    "approval_requests",
    "automation_outbox",
)


def upgrade() -> None:
    op.add_column("deals", sa.Column("discount_percent", sa.Numeric(5, 2)))

    op.create_table(
        "message_templates",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("channel", sa.String(40), nullable=False),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_message_templates_tenant"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "created_by_id"],
            ["memberships.tenant_id", "memberships.user_id"],
            name="fk_message_templates_tenant_created_by_id",
        ),
        sa.UniqueConstraint("tenant_id", "id", name="uq_message_templates_tenant_id"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_message_templates_tenant_name"),
    )

    op.create_table(
        "automation_workflows",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("trigger_type", sa.String(50), nullable=False),
        sa.Column("conditions_json", sa.Text(), nullable=False),
        sa.Column("condition_logic", sa.String(10), nullable=False),
        sa.Column("actions_json", sa.Text(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=False),
        sa.Column("updated_by_id", sa.UUID(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "trigger_type IN ('lead.created', 'deal.created', 'deal.updated', "
            "'deal.stage_changed', 'communication.created', 'schedule.deal_inactive')",
            name="ck_automation_workflows_trigger",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_automation_workflows_tenant"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "created_by_id"],
            ["memberships.tenant_id", "memberships.user_id"],
            name="fk_automation_workflows_tenant_created_by_id",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "updated_by_id"],
            ["memberships.tenant_id", "memberships.user_id"],
            name="fk_automation_workflows_tenant_updated_by_id",
        ),
        sa.UniqueConstraint("tenant_id", "id", name="uq_automation_workflows_tenant_id"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_automation_workflows_tenant_name"),
    )

    op.create_table(
        "automation_runs",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("workflow_id", sa.UUID(), nullable=False),
        sa.Column("event_key", sa.String(255), nullable=False),
        sa.Column("trigger_type", sa.String(50), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.UUID(), nullable=False),
        sa.Column("actor_id", sa.UUID()),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("context_json", sa.Text(), nullable=False),
        sa.Column("result_json", sa.Text(), nullable=False),
        sa.Column("error", sa.Text()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "status IN ('running', 'succeeded', 'failed', 'skipped')",
            name="ck_automation_runs_status",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_automation_runs_tenant"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "workflow_id"],
            ["automation_workflows.tenant_id", "automation_workflows.id"],
            name="fk_automation_runs_tenant_workflow_id",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "actor_id"],
            ["memberships.tenant_id", "memberships.user_id"],
            name="fk_automation_runs_tenant_actor_id",
        ),
        sa.UniqueConstraint("tenant_id", "id", name="uq_automation_runs_tenant_id"),
        sa.UniqueConstraint(
            "tenant_id", "workflow_id", "event_key", name="uq_automation_runs_event"
        ),
    )

    op.create_table(
        "approval_requests",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("workflow_id", sa.UUID(), nullable=False),
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("reason", sa.Text()),
        sa.Column("requested_by_id", sa.UUID()),
        sa.Column("assigned_to_id", sa.UUID()),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("continuation_json", sa.Text(), nullable=False),
        sa.Column("decision_comment", sa.Text()),
        sa.Column("decided_by_id", sa.UUID()),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'cancelled')",
            name="ck_approval_requests_status",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_approval_requests_tenant"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "workflow_id"],
            ["automation_workflows.tenant_id", "automation_workflows.id"],
            name="fk_approval_requests_tenant_workflow_id",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "run_id"],
            ["automation_runs.tenant_id", "automation_runs.id"],
            name="fk_approval_requests_tenant_run_id",
        ),
        *(
            sa.ForeignKeyConstraint(
                ["tenant_id", column],
                ["memberships.tenant_id", "memberships.user_id"],
                name=f"fk_approval_requests_tenant_{column}",
            )
            for column in ("requested_by_id", "assigned_to_id", "decided_by_id")
        ),
        sa.UniqueConstraint("tenant_id", "id", name="uq_approval_requests_tenant_id"),
    )

    op.create_table(
        "automation_outbox",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("template_id", sa.UUID(), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.UUID(), nullable=False),
        sa.Column("channel", sa.String(40), nullable=False),
        sa.Column("recipient", sa.String(255), nullable=False),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'sending', 'sent', 'failed', 'cancelled')",
            name="ck_automation_outbox_status",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_automation_outbox_tenant"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "run_id"],
            ["automation_runs.tenant_id", "automation_runs.id"],
            name="fk_automation_outbox_tenant_run_id",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "template_id"],
            ["message_templates.tenant_id", "message_templates.id"],
            name="fk_automation_outbox_tenant_template_id",
        ),
        sa.UniqueConstraint("tenant_id", "id", name="uq_automation_outbox_tenant_id"),
    )

    indexes = {
        "message_templates": ("tenant_id",),
        "automation_workflows": ("tenant_id", "trigger_type", "is_active"),
        "automation_runs": (
            "tenant_id",
            "workflow_id",
            "trigger_type",
            "entity_type",
            "entity_id",
            "actor_id",
            "status",
        ),
        "approval_requests": (
            "tenant_id",
            "workflow_id",
            "run_id",
            "entity_type",
            "entity_id",
            "requested_by_id",
            "assigned_to_id",
            "decided_by_id",
            "status",
        ),
        "automation_outbox": ("tenant_id", "run_id", "template_id", "status"),
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
            op.execute(sa.text(f'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE "{table}" TO cmr_app'))


def downgrade() -> None:
    for table in reversed(TENANT_TABLES):
        op.drop_table(table)
    op.drop_column("deals", "discount_percent")
