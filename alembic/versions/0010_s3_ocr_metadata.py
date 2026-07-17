"""s3 and ocr metadata

Revision ID: 0010_s3_ocr_metadata
Revises: 0009_pgvector_storage
Create Date: 2026-07-17
"""

from alembic import op
import sqlalchemy as sa


revision = "0010_s3_ocr_metadata"
down_revision = "0009_pgvector_storage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    file_columns = {item["name"] for item in sa.inspect(bind).get_columns("files")}
    document_columns = {
        item["name"] for item in sa.inspect(bind).get_columns("knowledge_documents")
    }

    if "storage_backend" not in file_columns:
        op.add_column("files", sa.Column("storage_backend", sa.String(length=40), nullable=True))
    if "extraction_method" not in document_columns:
        op.add_column(
            "knowledge_documents",
            sa.Column("extraction_method", sa.String(length=40), nullable=True),
        )
    if "source_pages" not in document_columns:
        op.add_column("knowledge_documents", sa.Column("source_pages", sa.Integer(), nullable=True))

    op.execute("UPDATE files SET storage_backend = 'local' WHERE storage_backend IS NULL")
    op.execute(
        "UPDATE knowledge_documents SET extraction_method = 'manual' "
        "WHERE extraction_method IS NULL"
    )

    with op.batch_alter_table("files") as batch_op:
        batch_op.alter_column("storage_backend", nullable=False)
    with op.batch_alter_table("knowledge_documents") as batch_op:
        batch_op.alter_column("extraction_method", nullable=False)


def downgrade() -> None:
    bind = op.get_bind()
    file_columns = {item["name"] for item in sa.inspect(bind).get_columns("files")}
    document_columns = {
        item["name"] for item in sa.inspect(bind).get_columns("knowledge_documents")
    }
    with op.batch_alter_table("knowledge_documents") as batch_op:
        for name in ("source_pages", "extraction_method"):
            if name in document_columns:
                batch_op.drop_column(name)
    if "storage_backend" in file_columns:
        with op.batch_alter_table("files") as batch_op:
            batch_op.drop_column("storage_backend")
