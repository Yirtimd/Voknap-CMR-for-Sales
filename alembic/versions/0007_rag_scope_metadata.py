"""rag scope metadata

Revision ID: 0007_rag_scope_metadata
Revises: 0006_communication_hub
Create Date: 2026-07-13
"""

from alembic import op
import sqlalchemy as sa


revision = "0007_rag_scope_metadata"
down_revision = "0006_communication_hub"
branch_labels = None
depends_on = None


def upgrade() -> None:
    _add_column_if_missing("knowledge_chunks", "scope", sa.Column("scope", sa.String(length=40), nullable=True))
    _add_column_if_missing("knowledge_chunks", "company_id", sa.Column("company_id", sa.Uuid(), nullable=True))
    _add_column_if_missing("knowledge_chunks", "deal_id", sa.Column("deal_id", sa.Uuid(), nullable=True))
    _add_column_if_missing("knowledge_queries", "scope", sa.Column("scope", sa.String(length=40), nullable=True))
    _add_column_if_missing("knowledge_queries", "company_id", sa.Column("company_id", sa.Uuid(), nullable=True))
    _add_column_if_missing("knowledge_queries", "deal_id", sa.Column("deal_id", sa.Uuid(), nullable=True))
    _add_column_if_missing("knowledge_queries", "include_global", sa.Column("include_global", sa.Boolean(), nullable=True))

    op.execute(
        """
        UPDATE knowledge_chunks
        SET scope = COALESCE((
                SELECT knowledge_documents.visibility
                FROM knowledge_documents
                WHERE knowledge_documents.id = knowledge_chunks.document_id
            ), 'global'),
            company_id = (
                SELECT knowledge_documents.company_id
                FROM knowledge_documents
                WHERE knowledge_documents.id = knowledge_chunks.document_id
            ),
            deal_id = (
                SELECT knowledge_documents.deal_id
                FROM knowledge_documents
                WHERE knowledge_documents.id = knowledge_chunks.document_id
            )
        """
    )
    op.execute("UPDATE knowledge_queries SET scope = 'global' WHERE scope IS NULL")
    op.execute("UPDATE knowledge_queries SET include_global = false WHERE include_global IS NULL")

    for table_name, column_name in (
        ("knowledge_chunks", "scope"),
        ("knowledge_chunks", "company_id"),
        ("knowledge_chunks", "deal_id"),
        ("knowledge_queries", "scope"),
        ("knowledge_queries", "company_id"),
        ("knowledge_queries", "deal_id"),
    ):
        _create_index_if_missing(f"ix_{table_name}_{column_name}", table_name, [column_name])
    _create_fk_if_missing("knowledge_chunks", "fk_knowledge_chunks_company_id_companies", ["company_id"], "companies", ["id"])
    _create_fk_if_missing("knowledge_chunks", "fk_knowledge_chunks_deal_id_deals", ["deal_id"], "deals", ["id"])
    _create_fk_if_missing("knowledge_queries", "fk_knowledge_queries_company_id_companies", ["company_id"], "companies", ["id"])
    _create_fk_if_missing("knowledge_queries", "fk_knowledge_queries_deal_id_deals", ["deal_id"], "deals", ["id"])


def downgrade() -> None:
    _drop_fk_if_present("knowledge_queries", "fk_knowledge_queries_deal_id_deals")
    _drop_fk_if_present("knowledge_queries", "fk_knowledge_queries_company_id_companies")
    _drop_fk_if_present("knowledge_chunks", "fk_knowledge_chunks_deal_id_deals")
    _drop_fk_if_present("knowledge_chunks", "fk_knowledge_chunks_company_id_companies")
    for table_name, column_name in (
        ("knowledge_chunks", "scope"),
        ("knowledge_chunks", "company_id"),
        ("knowledge_chunks", "deal_id"),
        ("knowledge_queries", "scope"),
        ("knowledge_queries", "company_id"),
        ("knowledge_queries", "deal_id"),
    ):
        _drop_index_if_present(f"ix_{table_name}_{column_name}", table_name)
    _drop_columns_if_present("knowledge_queries", ["include_global", "deal_id", "company_id", "scope"])
    _drop_columns_if_present("knowledge_chunks", ["deal_id", "company_id", "scope"])


def _add_column_if_missing(table_name: str, column_name: str, column: sa.Column) -> None:
    bind = op.get_bind()
    columns = {item["name"] for item in sa.inspect(bind).get_columns(table_name)}
    if column_name not in columns:
        op.add_column(table_name, column)


def _create_index_if_missing(index_name: str, table_name: str, columns: list[str]) -> None:
    bind = op.get_bind()
    indexes = {item["name"] for item in sa.inspect(bind).get_indexes(table_name)}
    if index_name not in indexes:
        op.create_index(index_name, table_name, columns)


def _drop_index_if_present(index_name: str, table_name: str) -> None:
    bind = op.get_bind()
    indexes = {item["name"] for item in sa.inspect(bind).get_indexes(table_name)}
    if index_name in indexes:
        op.drop_index(index_name, table_name=table_name)


def _drop_columns_if_present(table_name: str, column_names: list[str]) -> None:
    bind = op.get_bind()
    columns = {item["name"] for item in sa.inspect(bind).get_columns(table_name)}
    with op.batch_alter_table(table_name) as batch_op:
        for column_name in column_names:
            if column_name in columns:
                batch_op.drop_column(column_name)


def _create_fk_if_missing(
    table_name: str,
    constraint_name: str,
    local_columns: list[str],
    remote_table: str,
    remote_columns: list[str],
) -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return
    constraints = {item["name"] for item in sa.inspect(bind).get_foreign_keys(table_name)}
    if constraint_name not in constraints:
        op.create_foreign_key(constraint_name, table_name, remote_table, local_columns, remote_columns)


def _drop_fk_if_present(table_name: str, constraint_name: str) -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return
    constraints = {item["name"] for item in sa.inspect(bind).get_foreign_keys(table_name)}
    if constraint_name in constraints:
        op.drop_constraint(constraint_name, table_name, type_="foreignkey")
