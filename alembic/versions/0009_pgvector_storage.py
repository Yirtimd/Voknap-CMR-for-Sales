"""pgvector storage

Revision ID: 0009_pgvector_storage
Revises: 0008_embedding_metadata
Create Date: 2026-07-17
"""

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import VECTOR


revision = "0009_pgvector_storage"
down_revision = "0008_embedding_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    columns = {item["name"] for item in sa.inspect(bind).get_columns("knowledge_chunks")}

    if dialect == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    if "embedding_vector" not in columns:
        column_type = VECTOR(1536) if dialect == "postgresql" else sa.Text()
        op.add_column(
            "knowledge_chunks",
            sa.Column("embedding_vector", column_type, nullable=True),
        )

    if "embedding_json" in columns:
        if dialect == "postgresql":
            op.execute(
                """
                UPDATE knowledge_chunks
                SET embedding_vector = embedding_json::vector
                WHERE embedding_dimensions = 1536
                """
            )
        else:
            op.execute(
                "UPDATE knowledge_chunks SET embedding_vector = embedding_json "
                "WHERE embedding_dimensions = 1536"
            )

    missing = bind.execute(
        sa.text("SELECT count(*) FROM knowledge_chunks WHERE embedding_vector IS NULL")
    ).scalar_one()
    if missing:
        raise RuntimeError(
            f"Cannot migrate {missing} chunks to vector(1536); reindex them with the active model first"
        )

    if dialect == "postgresql":
        op.alter_column("knowledge_chunks", "embedding_vector", nullable=False)
        if "embedding_json" in columns:
            op.drop_column("knowledge_chunks", "embedding_json")
    else:
        with op.batch_alter_table("knowledge_chunks") as batch_op:
            batch_op.alter_column("embedding_vector", nullable=False)
            if "embedding_json" in columns:
                batch_op.drop_column("embedding_json")


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    columns = {item["name"] for item in sa.inspect(bind).get_columns("knowledge_chunks")}

    if "embedding_json" not in columns:
        op.add_column("knowledge_chunks", sa.Column("embedding_json", sa.Text(), nullable=True))

    if "embedding_vector" in columns:
        if dialect == "postgresql":
            op.execute("UPDATE knowledge_chunks SET embedding_json = embedding_vector::text")
            op.alter_column("knowledge_chunks", "embedding_json", nullable=False)
            op.drop_column("knowledge_chunks", "embedding_vector")
        else:
            op.execute("UPDATE knowledge_chunks SET embedding_json = embedding_vector")
            with op.batch_alter_table("knowledge_chunks") as batch_op:
                batch_op.alter_column("embedding_json", nullable=False)
                batch_op.drop_column("embedding_vector")
