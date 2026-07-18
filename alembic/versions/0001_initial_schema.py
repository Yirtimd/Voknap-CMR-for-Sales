"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-07-05
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


# Keep the initial migration independent from live ORM metadata. Importing current
# models here would silently change the historical schema whenever a model changes.
metadata = sa.MetaData()

tenants = sa.Table(
    "tenants",
    metadata,
    sa.Column("id", sa.UUID(), primary_key=True),
    sa.Column("name", sa.String(255), nullable=False),
    sa.Column("slug", sa.String(80), unique=True, nullable=False, index=True),
    sa.Column("is_active", sa.Boolean(), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
)

users = sa.Table(
    "users",
    metadata,
    sa.Column("id", sa.UUID(), primary_key=True),
    sa.Column("email", sa.String(255), unique=True, nullable=False, index=True),
    sa.Column("full_name", sa.String(255), nullable=False),
    sa.Column("password_hash", sa.String(255), nullable=False),
    sa.Column("is_active", sa.Boolean(), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
)

memberships = sa.Table(
    "memberships",
    metadata,
    sa.Column("id", sa.UUID(), primary_key=True),
    sa.Column("tenant_id", sa.UUID(), sa.ForeignKey("tenants.id"), nullable=False, index=True),
    sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id"), nullable=False, index=True),
    sa.Column("role", sa.String(40), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.UniqueConstraint("tenant_id", "user_id", name="uq_membership_tenant_user"),
)

companies = sa.Table(
    "companies",
    metadata,
    sa.Column("id", sa.UUID(), primary_key=True),
    sa.Column("tenant_id", sa.UUID(), nullable=False, index=True),
    sa.Column("name", sa.String(255), nullable=False),
    sa.Column("website", sa.String(255)),
    sa.Column("industry", sa.String(120)),
    sa.Column("description", sa.Text()),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
)

contacts = sa.Table(
    "contacts",
    metadata,
    sa.Column("id", sa.UUID(), primary_key=True),
    sa.Column("tenant_id", sa.UUID(), nullable=False, index=True),
    sa.Column("company_id", sa.UUID(), sa.ForeignKey("companies.id"), nullable=False, index=True),
    sa.Column("name", sa.String(255), nullable=False),
    sa.Column("phone", sa.String(80)),
    sa.Column("email", sa.String(255)),
    sa.Column("company_name", sa.String(255)),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
)

pipelines = sa.Table(
    "pipelines",
    metadata,
    sa.Column("id", sa.UUID(), primary_key=True),
    sa.Column("tenant_id", sa.UUID(), nullable=False, index=True),
    sa.Column("name", sa.String(120), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
)

pipeline_stages = sa.Table(
    "pipeline_stages",
    metadata,
    sa.Column("id", sa.UUID(), primary_key=True),
    sa.Column("tenant_id", sa.UUID(), nullable=False, index=True),
    sa.Column("pipeline_id", sa.UUID(), sa.ForeignKey("pipelines.id"), nullable=False),
    sa.Column("name", sa.String(120), nullable=False),
    sa.Column("sort_order", sa.Integer(), nullable=False),
)

leads = sa.Table(
    "leads",
    metadata,
    sa.Column("id", sa.UUID(), primary_key=True),
    sa.Column("tenant_id", sa.UUID(), nullable=False, index=True),
    sa.Column("company_id", sa.UUID(), sa.ForeignKey("companies.id"), nullable=False, index=True),
    sa.Column("contact_id", sa.UUID(), sa.ForeignKey("contacts.id")),
    sa.Column("title", sa.String(255), nullable=False),
    sa.Column("source", sa.String(80)),
    sa.Column("status", sa.String(80), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
)

deals = sa.Table(
    "deals",
    metadata,
    sa.Column("id", sa.UUID(), primary_key=True),
    sa.Column("tenant_id", sa.UUID(), nullable=False, index=True),
    sa.Column("company_id", sa.UUID(), sa.ForeignKey("companies.id"), nullable=False, index=True),
    sa.Column("lead_id", sa.UUID(), sa.ForeignKey("leads.id")),
    sa.Column("stage_id", sa.UUID(), sa.ForeignKey("pipeline_stages.id"), nullable=False),
    sa.Column("title", sa.String(255), nullable=False),
    sa.Column("amount", sa.Numeric(12, 2)),
    sa.Column("status", sa.String(40), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
)

tasks = sa.Table(
    "tasks",
    metadata,
    sa.Column("id", sa.UUID(), primary_key=True),
    sa.Column("tenant_id", sa.UUID(), nullable=False, index=True),
    sa.Column("company_id", sa.UUID(), sa.ForeignKey("companies.id"), nullable=False, index=True),
    sa.Column("assigned_to_id", sa.UUID(), sa.ForeignKey("users.id"), nullable=False),
    sa.Column("deal_id", sa.UUID(), sa.ForeignKey("deals.id")),
    sa.Column("title", sa.String(255), nullable=False),
    sa.Column("description", sa.Text()),
    sa.Column("due_at", sa.DateTime(timezone=True)),
    sa.Column("done_at", sa.DateTime(timezone=True)),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
)

notes = sa.Table(
    "notes",
    metadata,
    sa.Column("id", sa.UUID(), primary_key=True),
    sa.Column("tenant_id", sa.UUID(), nullable=False, index=True),
    sa.Column("company_id", sa.UUID(), sa.ForeignKey("companies.id"), nullable=False, index=True),
    sa.Column("author_id", sa.UUID(), sa.ForeignKey("users.id"), nullable=False),
    sa.Column("lead_id", sa.UUID(), sa.ForeignKey("leads.id")),
    sa.Column("deal_id", sa.UUID(), sa.ForeignKey("deals.id")),
    sa.Column("text", sa.Text(), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
)

activities = sa.Table(
    "activities",
    metadata,
    sa.Column("id", sa.UUID(), primary_key=True),
    sa.Column("tenant_id", sa.UUID(), nullable=False, index=True),
    sa.Column("company_id", sa.UUID(), sa.ForeignKey("companies.id"), nullable=False, index=True),
    sa.Column("contact_id", sa.UUID(), index=True),
    sa.Column("deal_id", sa.UUID(), index=True),
    sa.Column("type", sa.String(40), nullable=False, index=True),
    sa.Column("title", sa.String(255), nullable=False),
    sa.Column("description", sa.Text()),
    sa.Column("created_by", sa.UUID(), index=True),
    sa.Column("metadata_json", sa.Text(), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, index=True),
)

knowledge_documents = sa.Table(
    "knowledge_documents",
    metadata,
    sa.Column("id", sa.UUID(), primary_key=True),
    sa.Column("tenant_id", sa.UUID(), nullable=False, index=True),
    sa.Column("title", sa.String(255), nullable=False),
    sa.Column("source_type", sa.String(40), nullable=False),
    sa.Column("status", sa.String(40), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
)

knowledge_chunks = sa.Table(
    "knowledge_chunks",
    metadata,
    sa.Column("id", sa.UUID(), primary_key=True),
    sa.Column("tenant_id", sa.UUID(), nullable=False, index=True),
    sa.Column(
        "document_id",
        sa.UUID(),
        sa.ForeignKey("knowledge_documents.id"),
        nullable=False,
        index=True,
    ),
    sa.Column("chunk_index", sa.Integer(), nullable=False),
    sa.Column("text", sa.Text(), nullable=False),
    sa.Column("embedding_json", sa.Text(), nullable=False),
    sa.Column("token_estimate", sa.Integer(), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
)

knowledge_queries = sa.Table(
    "knowledge_queries",
    metadata,
    sa.Column("id", sa.UUID(), primary_key=True),
    sa.Column("tenant_id", sa.UUID(), nullable=False, index=True),
    sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id"), nullable=False),
    sa.Column("question", sa.Text(), nullable=False),
    sa.Column("answer", sa.Text(), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
)

agent_messages = sa.Table(
    "agent_messages",
    metadata,
    sa.Column("id", sa.UUID(), primary_key=True),
    sa.Column("tenant_id", sa.UUID(), nullable=False, index=True),
    sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id"), nullable=False),
    sa.Column("role", sa.String(40), nullable=False),
    sa.Column("content", sa.Text(), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
)

agent_actions = sa.Table(
    "agent_actions",
    metadata,
    sa.Column("id", sa.UUID(), primary_key=True),
    sa.Column("tenant_id", sa.UUID(), nullable=False, index=True),
    sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id"), nullable=False),
    sa.Column("action_type", sa.String(80), nullable=False),
    sa.Column("status", sa.String(40), nullable=False),
    sa.Column("payload_json", sa.Text(), nullable=False),
    sa.Column("result_json", sa.Text()),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("confirmed_at", sa.DateTime(timezone=True)),
)

connector_accounts = sa.Table(
    "connector_accounts",
    metadata,
    sa.Column("id", sa.UUID(), primary_key=True),
    sa.Column("tenant_id", sa.UUID(), nullable=False, index=True),
    sa.Column("connector_code", sa.String(80), nullable=False),
    sa.Column("title", sa.String(255), nullable=False),
    sa.Column("status", sa.String(40), nullable=False),
    sa.Column("credentials_json", sa.Text(), nullable=False),
    sa.Column("settings_json", sa.Text(), nullable=False),
    sa.Column("last_sync_at", sa.DateTime(timezone=True)),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
)

connector_sync_runs = sa.Table(
    "connector_sync_runs",
    metadata,
    sa.Column("id", sa.UUID(), primary_key=True),
    sa.Column("tenant_id", sa.UUID(), nullable=False, index=True),
    sa.Column("account_id", sa.UUID(), sa.ForeignKey("connector_accounts.id"), nullable=False),
    sa.Column("direction", sa.String(40), nullable=False),
    sa.Column("status", sa.String(40), nullable=False),
    sa.Column("created_count", sa.Integer(), nullable=False),
    sa.Column("updated_count", sa.Integer(), nullable=False),
    sa.Column("failed_count", sa.Integer(), nullable=False),
    sa.Column("message", sa.Text()),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
)

applied_templates = sa.Table(
    "applied_templates",
    metadata,
    sa.Column("id", sa.UUID(), primary_key=True),
    sa.Column("tenant_id", sa.UUID(), nullable=False, index=True),
    sa.Column("template_code", sa.String(80), nullable=False),
    sa.Column("template_title", sa.String(255), nullable=False),
    sa.Column("status", sa.String(40), nullable=False),
    sa.Column("result_json", sa.Text(), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
)

audit_logs = sa.Table(
    "audit_logs",
    metadata,
    sa.Column("id", sa.UUID(), primary_key=True),
    sa.Column("tenant_id", sa.UUID(), nullable=False, index=True),
    sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id")),
    sa.Column("action", sa.String(120), nullable=False),
    sa.Column("entity_type", sa.String(120)),
    sa.Column("entity_id", sa.String(120)),
    sa.Column("payload_json", sa.Text(), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
)

feature_flags = sa.Table(
    "feature_flags",
    metadata,
    sa.Column("id", sa.UUID(), primary_key=True),
    sa.Column("tenant_id", sa.UUID(), nullable=False, index=True),
    sa.Column("code", sa.String(120), nullable=False),
    sa.Column("title", sa.String(255), nullable=False),
    sa.Column("enabled", sa.Boolean(), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
)

tenant_plans = sa.Table(
    "tenant_plans",
    metadata,
    sa.Column("id", sa.UUID(), primary_key=True),
    sa.Column("tenant_id", sa.UUID(), nullable=False, index=True),
    sa.Column("plan_code", sa.String(80), nullable=False),
    sa.Column("users_limit", sa.Integer(), nullable=False),
    sa.Column("leads_limit", sa.Integer(), nullable=False),
    sa.Column("documents_limit", sa.Integer(), nullable=False),
    sa.Column("ai_requests_limit", sa.Integer(), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
)


def upgrade() -> None:
    metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    metadata.drop_all(bind=op.get_bind())

