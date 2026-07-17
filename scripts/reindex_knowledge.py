from __future__ import annotations

import argparse
import sys
from pathlib import Path
from uuid import UUID


sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.config import settings
from app.core.database import SessionLocal
from app.modules.knowledge.service import KnowledgeService


def main() -> None:
    parser = argparse.ArgumentParser(description="Reindex RAG chunks using configured embeddings")
    parser.add_argument("--tenant-id", type=UUID, default=None)
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args()
    if args.batch_size < 1:
        parser.error("--batch-size must be greater than zero")

    db = SessionLocal()
    try:
        count = KnowledgeService(db).reindex_all(args.tenant_id, args.batch_size)
        print(
            f"Reindexed {count} chunks with "
            f"{settings.embedding_provider}/{settings.embedding_model} "
            f"version {settings.embedding_version}."
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
