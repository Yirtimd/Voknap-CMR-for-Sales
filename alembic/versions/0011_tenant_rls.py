"""tenant row-level security

Revision ID: 0011_tenant_rls
Revises: 0010_s3_ocr_metadata
Create Date: 2026-07-18
"""

from alembic import op
import sqlalchemy as sa


revision = "0011_tenant_rls"
down_revision = "0010_s3_ocr_metadata"
branch_labels = None
depends_on = None


TENANT_TABLES = (
    "activities",
    "agent_actions",
    "agent_messages",
    "applied_templates",
    "audit_logs",
    "communication_events",
    "companies",
    "connector_accounts",
    "connector_sync_runs",
    "contacts",
    "customer_insights",
    "deals",
    "feature_flags",
    "files",
    "knowledge_chunks",
    "knowledge_documents",
    "knowledge_queries",
    "leads",
    "next_actions",
    "notes",
    "pipeline_stages",
    "pipelines",
    "tasks",
    "tenant_plans",
)


TENANT_RELATIONS = (
    ("contacts", ("tenant_id", "company_id"), "companies"),
    ("pipeline_stages", ("tenant_id", "pipeline_id"), "pipelines"),
    ("leads", ("tenant_id", "company_id"), "companies"),
    ("leads", ("tenant_id", "contact_id"), "contacts"),
    ("deals", ("tenant_id", "company_id"), "companies"),
    ("deals", ("tenant_id", "lead_id"), "leads"),
    ("deals", ("tenant_id", "stage_id"), "pipeline_stages"),
    ("deals", ("tenant_id", "next_action_id"), "next_actions"),
    ("companies", ("tenant_id", "next_action_id"), "next_actions"),
    ("tasks", ("tenant_id", "company_id"), "companies"),
    ("tasks", ("tenant_id", "deal_id"), "deals"),
    ("notes", ("tenant_id", "company_id"), "companies"),
    ("notes", ("tenant_id", "lead_id"), "leads"),
    ("notes", ("tenant_id", "deal_id"), "deals"),
    ("next_actions", ("tenant_id", "company_id"), "companies"),
    ("next_actions", ("tenant_id", "deal_id"), "deals"),
    ("next_actions", ("tenant_id", "contact_id"), "contacts"),
    ("activities", ("tenant_id", "company_id"), "companies"),
    ("activities", ("tenant_id", "contact_id"), "contacts"),
    ("activities", ("tenant_id", "deal_id"), "deals"),
    ("files", ("tenant_id", "company_id"), "companies"),
    ("files", ("tenant_id", "deal_id"), "deals"),
    ("files", ("tenant_id", "contact_id"), "contacts"),
    ("files", ("tenant_id", "activity_id"), "activities"),
    ("customer_insights", ("tenant_id", "company_id"), "companies"),
    ("connector_sync_runs", ("tenant_id", "account_id"), "connector_accounts"),
    ("communication_events", ("tenant_id", "company_id"), "companies"),
    ("communication_events", ("tenant_id", "contact_id"), "contacts"),
    ("communication_events", ("tenant_id", "deal_id"), "deals"),
    ("communication_events", ("tenant_id", "activity_id"), "activities"),
    (
        "communication_events",
        ("tenant_id", "connector_account_id"),
        "connector_accounts",
    ),
    ("knowledge_documents", ("tenant_id", "company_id"), "companies"),
    ("knowledge_documents", ("tenant_id", "deal_id"), "deals"),
    ("knowledge_documents", ("tenant_id", "file_id"), "files"),
    ("knowledge_chunks", ("tenant_id", "document_id"), "knowledge_documents"),
    ("knowledge_chunks", ("tenant_id", "company_id"), "companies"),
    ("knowledge_chunks", ("tenant_id", "deal_id"), "deals"),
    ("knowledge_queries", ("tenant_id", "company_id"), "companies"),
    ("knowledge_queries", ("tenant_id", "deal_id"), "deals"),
)


MEMBERSHIP_RELATIONS = (
    ("companies", "owner_id"),
    ("deals", "owner_id"),
    ("tasks", "assigned_to_id"),
    ("notes", "author_id"),
    ("next_actions", "assigned_to_id"),
    ("activities", "created_by"),
    ("files", "uploaded_by_id"),
    ("communication_events", "created_by"),
    ("audit_logs", "user_id"),
    ("knowledge_queries", "user_id"),
    ("agent_messages", "user_id"),
    ("agent_actions", "user_id"),
)


def _relation_name(table: str, column: str) -> str:
    return f"fk_{table}_tenant_{column}"


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'cmr_app') THEN
                CREATE ROLE cmr_app NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
                    NOINHERIT NOREPLICATION NOBYPASSRLS;
            END IF;
        END
        $$
        """
    )
    op.execute(
        "ALTER ROLE cmr_app NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE "
        "NOINHERIT NOREPLICATION NOBYPASSRLS"
    )
    op.execute("GRANT USAGE ON SCHEMA public TO cmr_app")
    op.execute("GRANT cmr_app TO CURRENT_USER")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO cmr_app")
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO cmr_app"
    )

    for table in TENANT_TABLES:
        op.create_foreign_key(
            f"fk_{table}_tenant",
            table,
            "tenants",
            ["tenant_id"],
            ["id"],
        )
        op.create_unique_constraint(f"uq_{table}_tenant_id", table, ["tenant_id", "id"])

    for table, columns, target in TENANT_RELATIONS:
        column = columns[1]
        op.create_foreign_key(
            _relation_name(table, column),
            table,
            target,
            list(columns),
            ["tenant_id", "id"],
        )

    for table, user_column in MEMBERSHIP_RELATIONS:
        op.create_foreign_key(
            _relation_name(table, user_column),
            table,
            "memberships",
            ["tenant_id", user_column],
            ["tenant_id", "user_id"],
        )

    tenant_predicate = (
        "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"
    )
    for table in TENANT_TABLES:
        op.execute(sa.text(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY'))
        op.execute(sa.text(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY'))
        op.execute(
            sa.text(
                f'CREATE POLICY tenant_isolation ON "{table}" '
                f"USING ({tenant_predicate}) WITH CHECK ({tenant_predicate})"
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    for table in reversed(TENANT_TABLES):
        op.execute(sa.text(f'DROP POLICY IF EXISTS tenant_isolation ON "{table}"'))
        op.execute(sa.text(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY'))

    for table, user_column in reversed(MEMBERSHIP_RELATIONS):
        op.drop_constraint(_relation_name(table, user_column), table, type_="foreignkey")

    for table, columns, _target in reversed(TENANT_RELATIONS):
        op.drop_constraint(_relation_name(table, columns[1]), table, type_="foreignkey")

    for table in reversed(TENANT_TABLES):
        op.drop_constraint(f"uq_{table}_tenant_id", table, type_="unique")
        op.drop_constraint(f"fk_{table}_tenant", table, type_="foreignkey")

    op.execute("REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM cmr_app")
    op.execute("REVOKE USAGE ON SCHEMA public FROM cmr_app")
    op.execute("REVOKE cmr_app FROM CURRENT_USER")
    op.execute("DROP ROLE IF EXISTS cmr_app")
