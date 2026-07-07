"""company knowledge scope

Revision ID: 0004_company_knowledge_scope
Revises: 0003_data_model_hardening
Create Date: 2026-07-07
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_company_knowledge_scope"
down_revision = "0003_data_model_hardening"
branch_labels = None
depends_on = None


def upgrade() -> None:
    _add_column_if_missing("knowledge_documents", "company_id", sa.Column("company_id", sa.UUID(), nullable=True))
    _add_column_if_missing("knowledge_documents", "deal_id", sa.Column("deal_id", sa.UUID(), nullable=True))
    _add_column_if_missing("knowledge_documents", "file_id", sa.Column("file_id", sa.UUID(), nullable=True))
    _add_column_if_missing("knowledge_documents", "visibility", sa.Column("visibility", sa.String(length=40), nullable=True))

    _create_index_if_missing("ix_knowledge_documents_company_id", "knowledge_documents", ["company_id"])
    _create_index_if_missing("ix_knowledge_documents_deal_id", "knowledge_documents", ["deal_id"])
    _create_index_if_missing("ix_knowledge_documents_file_id", "knowledge_documents", ["file_id"])
    _create_fk_if_missing("knowledge_documents", "fk_knowledge_documents_company_id_companies", ["company_id"], "companies", ["id"])
    _create_fk_if_missing("knowledge_documents", "fk_knowledge_documents_deal_id_deals", ["deal_id"], "deals", ["id"])
    _create_fk_if_missing("knowledge_documents", "fk_knowledge_documents_file_id_files", ["file_id"], "files", ["id"])

    op.execute("UPDATE knowledge_documents SET visibility = 'global' WHERE visibility IS NULL")


def downgrade() -> None:
    _drop_fk_if_present("knowledge_documents", "fk_knowledge_documents_file_id_files")
    _drop_fk_if_present("knowledge_documents", "fk_knowledge_documents_deal_id_deals")
    _drop_fk_if_present("knowledge_documents", "fk_knowledge_documents_company_id_companies")
    _drop_index_if_present("ix_knowledge_documents_file_id", "knowledge_documents")
    _drop_index_if_present("ix_knowledge_documents_deal_id", "knowledge_documents")
    _drop_index_if_present("ix_knowledge_documents_company_id", "knowledge_documents")
    _drop_columns_if_present("knowledge_documents", ["visibility", "file_id", "deal_id", "company_id"])


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
