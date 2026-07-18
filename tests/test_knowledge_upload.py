from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.main  # noqa: F401 - registers all models
from app.core.database import Base
from app.core.database import get_db
from app.core.dependencies import CurrentTenant, get_current_tenant
from app.main import app
from app.modules.knowledge.service import KnowledgeService
from app.modules.sales.models import CompanyFile


def test_txt_upload_stores_file_document_chunks_and_metadata(tmp_path, monkeypatch):
    monkeypatch.setattr("app.modules.knowledge.files.settings.knowledge_upload_dir", str(tmp_path))
    monkeypatch.setattr("app.modules.knowledge.storage.settings.knowledge_storage_backend", "local")
    monkeypatch.setattr("app.modules.knowledge.service.settings.embedding_provider", "local")
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        document = KnowledgeService(db).create_document_from_upload(
            tenant_id=uuid4(),
            user_id=uuid4(),
            filename="sales-playbook.txt",
            content_type="text/plain",
            data=(
                "После новой заявки связаться с клиентом за 15 минут. "
                "Следующий шаг — квалификация и создание сделки."
            ).encode(),
        )
        stored_file = db.query(CompanyFile).filter(CompanyFile.id == document.file_id).one()

        assert document.title == "sales-playbook"
        assert document.source_type == "txt"
        assert document.visibility == "global"
        assert len(document.chunks) == 1
        assert document.chunks[0].embedding_provider == "local"
        assert document.chunks[0].embedding_dimensions == 1536
        assert (tmp_path / stored_file.storage_key).read_bytes().startswith("После новой заявки".encode())
        assert stored_file.download_url == f"/knowledge/documents/{document.id}/download"


def test_upload_and_authenticated_download_api(tmp_path, monkeypatch):
    monkeypatch.setattr("app.modules.knowledge.files.settings.knowledge_upload_dir", str(tmp_path))
    monkeypatch.setattr("app.modules.knowledge.storage.settings.knowledge_storage_backend", "local")
    monkeypatch.setattr("app.modules.knowledge.service.settings.embedding_provider", "local")
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = Session(engine)
    tenant = CurrentTenant(id=uuid4(), user_id=uuid4(), role="owner")

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_tenant] = lambda: tenant
    try:
        client = TestClient(app)
        response = client.post(
            "/knowledge/documents/upload",
            data={"scope": "global", "title": "API playbook"},
            files={
                "file": (
                    "playbook.txt",
                    "Первый контакт выполнить за 15 минут и создать следующую задачу.".encode(),
                    "text/plain",
                )
            },
        )

        assert response.status_code == 201, response.text
        payload = response.json()
        assert payload["title"] == "API playbook"
        assert payload["source_type"] == "txt"
        assert payload["chunks_count"] == 1
        download = client.get(payload["download_url"])
        assert download.status_code == 200
        assert download.content.startswith("Первый контакт".encode())
    finally:
        app.dependency_overrides.clear()
        db.close()
