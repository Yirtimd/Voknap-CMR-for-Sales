"""production foundations for approvals and sales operations

Revision ID: 0018_sales_production
Revises: 0017_real_integrations
Create Date: 2026-07-24
"""

from alembic import op
import sqlalchemy as sa


revision = "0018_sales_production"
down_revision = "0017_real_integrations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("pipelines", sa.Column("description", sa.Text()))
    op.add_column(
        "pipelines",
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.add_column(
        "pipelines",
        sa.Column("is_default", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "pipelines",
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
    )
    op.add_column(
        "pipelines",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_unique_constraint("uq_pipelines_tenant_name", "pipelines", ["tenant_id", "name"])
    op.create_index(
        "uq_pipelines_one_default",
        "pipelines",
        ["tenant_id"],
        unique=True,
        postgresql_where=sa.text("is_default"),
    )
    op.create_index("ix_pipelines_is_active", "pipelines", ["is_active"])
    op.create_index("ix_pipelines_is_default", "pipelines", ["is_default"])

    op.add_column("pipeline_stages", sa.Column("code", sa.String(80)))
    op.add_column(
        "pipeline_stages",
        sa.Column("probability", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "pipeline_stages",
        sa.Column("stage_type", sa.String(20), server_default="open", nullable=False),
    )
    op.add_column(
        "pipeline_stages",
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.add_column(
        "pipeline_stages",
        sa.Column("required_fields_json", sa.Text(), server_default="[]", nullable=False),
    )
    op.execute(
        sa.text(
            "UPDATE pipeline_stages SET code = "
            "'stage_' || replace(CAST(id AS VARCHAR), '-', '')"
        )
    )
    op.alter_column("pipeline_stages", "code", nullable=False)
    op.create_unique_constraint(
        "uq_pipeline_stages_code",
        "pipeline_stages",
        ["tenant_id", "pipeline_id", "code"],
    )
    op.create_check_constraint(
        "ck_pipeline_stages_type",
        "pipeline_stages",
        "stage_type IN ('open', 'won', 'lost')",
    )
    op.create_check_constraint(
        "ck_pipeline_stages_probability",
        "pipeline_stages",
        "probability >= 0 AND probability <= 100",
    )
    op.create_index("ix_pipeline_stages_is_active", "pipeline_stages", ["is_active"])

    op.create_table(
        "duplicate_candidates",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("entity_type", sa.String(20), nullable=False),
        sa.Column("record_a_id", sa.UUID(), nullable=False),
        sa.Column("record_b_id", sa.UUID(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("matched_fields_json", sa.Text(), server_default="[]", nullable=False),
        sa.Column("status", sa.String(20), server_default="open", nullable=False),
        sa.Column("detected_by_id", sa.UUID()),
        sa.Column("resolved_by_id", sa.UUID()),
        sa.Column("resolution_comment", sa.Text()),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "detected_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "entity_type IN ('contacts', 'leads', 'deals')",
            name="ck_duplicate_candidates_entity_type",
        ),
        sa.CheckConstraint(
            "status IN ('open', 'dismissed', 'merged')",
            name="ck_duplicate_candidates_status",
        ),
        sa.CheckConstraint(
            "score >= 0 AND score <= 100",
            name="ck_duplicate_candidates_score",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_duplicate_candidates_tenant"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "detected_by_id"],
            ["memberships.tenant_id", "memberships.user_id"],
            name="fk_duplicate_candidates_tenant_detected_by_id",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "resolved_by_id"],
            ["memberships.tenant_id", "memberships.user_id"],
            name="fk_duplicate_candidates_tenant_resolved_by_id",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "id", name="uq_duplicate_candidates_tenant_id"),
        sa.UniqueConstraint(
            "tenant_id",
            "entity_type",
            "record_a_id",
            "record_b_id",
            name="uq_duplicate_candidates_pair",
        ),
    )
    for column in (
        "tenant_id",
        "entity_type",
        "record_a_id",
        "record_b_id",
        "status",
        "detected_by_id",
        "resolved_by_id",
    ):
        op.create_index(op.f(f"ix_duplicate_candidates_{column}"), "duplicate_candidates", [column])

    op.drop_constraint("ck_automation_runs_status", "automation_runs", type_="check")
    op.create_check_constraint(
        "ck_automation_runs_status",
        "automation_runs",
        "status IN ('running', 'waiting_approval', 'succeeded', 'failed', 'skipped')",
    )
    op.drop_constraint("ck_approval_requests_status", "approval_requests", type_="check")
    op.create_check_constraint(
        "ck_approval_requests_status",
        "approval_requests",
        "status IN ('pending', 'approved', 'rejected', 'cancelled', 'expired')",
    )
    op.add_column(
        "approval_requests",
        sa.Column("priority", sa.String(20), server_default="normal", nullable=False),
    )
    op.add_column("approval_requests", sa.Column("due_at", sa.DateTime(timezone=True)))
    op.add_column(
        "approval_requests",
        sa.Column("context_snapshot_json", sa.Text(), server_default="{}", nullable=False),
    )
    op.add_column(
        "approval_requests",
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
    )
    op.add_column(
        "approval_requests",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_approval_requests_priority",
        "approval_requests",
        "priority IN ('low', 'normal', 'high', 'critical')",
    )
    op.create_index("ix_approval_requests_priority", "approval_requests", ["priority"])
    op.create_index("ix_approval_requests_due_at", "approval_requests", ["due_at"])

    op.create_table(
        "approval_history",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("approval_id", sa.UUID(), nullable=False),
        sa.Column("action", sa.String(40), nullable=False),
        sa.Column("from_status", sa.String(20)),
        sa.Column("to_status", sa.String(20)),
        sa.Column("actor_id", sa.UUID()),
        sa.Column("comment", sa.Text()),
        sa.Column("metadata_json", sa.Text(), server_default="{}", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_approval_history_tenant"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "approval_id"],
            ["approval_requests.tenant_id", "approval_requests.id"],
            name="fk_approval_history_tenant_approval_id",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "actor_id"],
            ["memberships.tenant_id", "memberships.user_id"],
            name="fk_approval_history_tenant_actor_id",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "id", name="uq_approval_history_tenant_id"),
    )
    for column in ("tenant_id", "approval_id", "actor_id"):
        op.create_index(op.f(f"ix_approval_history_{column}"), "approval_history", [column])

    if op.get_bind().dialect.name == "postgresql":
        predicate = "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"
        for table in ("approval_history", "duplicate_candidates"):
            op.execute(sa.text(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY'))
            op.execute(sa.text(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY'))
            op.execute(
                sa.text(
                    f'CREATE POLICY tenant_isolation ON "{table}" '
                    f"USING ({predicate}) WITH CHECK ({predicate})"
                )
            )
            op.execute(
                sa.text(f'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE "{table}" TO cmr_app')
            )


def downgrade() -> None:
    op.drop_table("duplicate_candidates")
    op.drop_table("approval_history")
    op.drop_index("ix_approval_requests_due_at", table_name="approval_requests")
    op.drop_index("ix_approval_requests_priority", table_name="approval_requests")
    op.drop_constraint("ck_approval_requests_priority", "approval_requests", type_="check")
    for column in ("updated_at", "version", "context_snapshot_json", "due_at", "priority"):
        op.drop_column("approval_requests", column)
    op.drop_constraint("ck_approval_requests_status", "approval_requests", type_="check")
    op.create_check_constraint(
        "ck_approval_requests_status",
        "approval_requests",
        "status IN ('pending', 'approved', 'rejected', 'cancelled')",
    )
    op.drop_constraint("ck_automation_runs_status", "automation_runs", type_="check")
    op.create_check_constraint(
        "ck_automation_runs_status",
        "automation_runs",
        "status IN ('running', 'succeeded', 'failed', 'skipped')",
    )
    op.drop_index("ix_pipeline_stages_is_active", table_name="pipeline_stages")
    op.drop_constraint("ck_pipeline_stages_probability", "pipeline_stages", type_="check")
    op.drop_constraint("ck_pipeline_stages_type", "pipeline_stages", type_="check")
    op.drop_constraint("uq_pipeline_stages_code", "pipeline_stages", type_="unique")
    for column in ("required_fields_json", "is_active", "stage_type", "probability", "code"):
        op.drop_column("pipeline_stages", column)
    op.drop_index("ix_pipelines_is_default", table_name="pipelines")
    op.drop_index("ix_pipelines_is_active", table_name="pipelines")
    op.drop_index("uq_pipelines_one_default", table_name="pipelines")
    op.drop_constraint("uq_pipelines_tenant_name", "pipelines", type_="unique")
    for column in ("updated_at", "version", "is_default", "is_active", "description"):
        op.drop_column("pipelines", column)
