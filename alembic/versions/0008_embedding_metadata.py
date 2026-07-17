"""embedding metadata

Revision ID: 0008_embedding_metadata
Revises: 0007_rag_scope_metadata
Create Date: 2026-07-17
"""

from alembic import op
import sqlalchemy as sa


revision = "0008_embedding_metadata"
down_revision = "0007_rag_scope_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {item["name"] for item in sa.inspect(op.get_bind()).get_columns("knowledge_chunks")}
    additions = (
        ("embedding_provider", sa.Column("embedding_provider", sa.String(length=50), nullable=True)),
        ("embedding_model", sa.Column("embedding_model", sa.String(length=120), nullable=True)),
        ("embedding_version", sa.Column("embedding_version", sa.String(length=40), nullable=True)),
        ("embedding_dimensions", sa.Column("embedding_dimensions", sa.Integer(), nullable=True)),
    )
    for name, column in additions:
        if name not in columns:
            op.add_column("knowledge_chunks", column)

    op.execute(
        """
        UPDATE knowledge_chunks
        SET embedding_provider = COALESCE(embedding_provider, 'local'),
            embedding_model = COALESCE(embedding_model, 'local-hash-v1'),
            embedding_version = COALESCE(embedding_version, '1'),
            embedding_dimensions = COALESCE(embedding_dimensions, 256)
        """
    )
    with op.batch_alter_table("knowledge_chunks") as batch_op:
        batch_op.alter_column("embedding_provider", nullable=False)
        batch_op.alter_column("embedding_model", nullable=False)
        batch_op.alter_column("embedding_version", nullable=False)
        batch_op.alter_column("embedding_dimensions", nullable=False)


def downgrade() -> None:
    columns = {item["name"] for item in sa.inspect(op.get_bind()).get_columns("knowledge_chunks")}
    with op.batch_alter_table("knowledge_chunks") as batch_op:
        for name in (
            "embedding_dimensions",
            "embedding_version",
            "embedding_model",
            "embedding_provider",
        ):
            if name in columns:
                batch_op.drop_column(name)
