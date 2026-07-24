import io
import json
from datetime import datetime, timezone
from uuid import uuid4

from openpyxl import Workbook
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main  # noqa: F401
from app.core.database import Base
from app.core.database import get_db
from app.modules.accounts.models import Membership, Tenant, User
from app.modules.connectors.api_keys import create_api_key
from app.modules.connectors.importers import apply_mapping, parse_import_file, suggest_mapping
from app.modules.connectors.jobs import IntegrationJobService
from app.modules.connectors.models import PublicApiKey
from app.modules.connectors.providers import fetch_calendar_events
from app.modules.connectors.service import ConnectorService
from app.modules.sales.models import Company


def make_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def seed_tenant(db):
    tenant_id = uuid4()
    user_id = uuid4()
    db.add(Tenant(id=tenant_id, name="Test", slug=f"test-{tenant_id.hex[:8]}"))
    db.add(
        User(
            id=user_id,
            email=f"{user_id.hex[:8]}@example.com",
            full_name="Owner",
            password_hash="hash",
            is_active=True,
        )
    )
    db.add(
        Membership(
            tenant_id=tenant_id,
            user_id=user_id,
            role="owner",
            is_active=True,
        )
    )
    db.commit()
    return tenant_id, user_id


def test_definitions_do_not_claim_placeholders_are_ready():
    definitions = ConnectorService(None).definitions()

    assert all(item.status != "placeholder" for item in definitions)
    assert {item.code for item in definitions if item.status == "requires_provider"} == {
        "telephony",
        "telegram_whatsapp",
        "onec",
    }


def test_csv_and_xlsx_preview_mapping():
    headers, csv_rows = parse_import_file(
        "contacts.csv",
        "Имя;Почта;Компания\nИван;ivan@example.com;Ромашка\n".encode(),
    )
    mapping = suggest_mapping(headers)
    mapped, errors = apply_mapping(csv_rows, mapping)

    assert mapped == [
        {"name": "Иван", "email": "ivan@example.com", "company_name": "Ромашка"}
    ]
    assert errors == []

    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["name", "email"])
    sheet.append(["Anna", "anna@example.com"])
    stream = io.BytesIO()
    workbook.save(stream)

    xlsx_headers, xlsx_rows = parse_import_file("contacts.xlsx", stream.getvalue())
    assert xlsx_headers == ["name", "email"]
    assert xlsx_rows[0]["email"] == "anna@example.com"


def test_job_idempotency_dead_letter_and_replay():
    db = make_db()
    tenant_id, user_id = seed_tenant(db)
    service = IntegrationJobService(db)

    first = service.enqueue(
        tenant_id=tenant_id,
        job_type="unsupported.test",
        idempotency_key="same-operation",
        payload={},
        created_by_id=user_id,
        max_attempts=1,
    )
    second = service.enqueue(
        tenant_id=tenant_id,
        job_type="unsupported.test",
        idempotency_key="same-operation",
        payload={"ignored": True},
        created_by_id=user_id,
        max_attempts=1,
    )

    assert first.id == second.id
    assert service.process_available() == 1
    db.refresh(first)
    assert first.status == "dead"
    assert json.loads(first.error_log_json)[0]["attempt"] == 1

    replayed = service.replay(tenant_id, first.id)
    assert replayed is not None
    assert replayed.status == "pending"
    assert replayed.attempt == 0


def test_public_api_key_is_only_returned_once_and_stored_hashed():
    db = make_db()
    tenant_id, user_id = seed_tenant(db)

    key, raw = create_api_key(
        db,
        tenant_id=tenant_id,
        title="ERP",
        scopes=["leads:read"],
        expires_at=datetime.now(timezone.utc),
        created_by_id=user_id,
    )
    stored = db.get(PublicApiKey, key.id)

    assert raw.startswith(f"voknap_live_{tenant_id.hex}_")
    assert raw not in stored.key_hash
    assert json.loads(stored.scopes_json) == ["leads:read"]


def test_google_calendar_incremental_sync_persists_next_token(monkeypatch):
    requests = []

    def fake_request(method, url, **kwargs):
        requests.append((method, url, kwargs.get("params")))
        return {
            "items": [
                {
                    "id": "event-1",
                    "summary": "Demo",
                    "start": {"dateTime": "2026-07-25T10:00:00Z"},
                    "end": {"dateTime": "2026-07-25T11:00:00Z"},
                }
            ],
            "nextSyncToken": "next-token",
        }

    monkeypatch.setattr("app.modules.connectors.providers._request_json", fake_request)

    events, cursor = fetch_calendar_events(
        "google_calendar",
        {"access_token": "token"},
        "previous-token",
    )

    assert requests[0][2]["syncToken"] == "previous-token"
    assert events[0]["id"] == "event-1"
    assert cursor == "next-token"


def test_public_api_key_authenticates_scoped_lead_create():
    db = make_db()
    tenant_id, user_id = seed_tenant(db)
    company = Company(tenant_id=tenant_id, name="API Company")
    db.add(company)
    db.commit()
    db.refresh(company)
    _key, raw = create_api_key(
        db,
        tenant_id=tenant_id,
        title="Integration",
        scopes=["leads:read", "leads:write"],
        expires_at=None,
        created_by_id=user_id,
    )

    def override_db():
        yield db

    app.main.app.dependency_overrides[get_db] = override_db
    try:
        client = TestClient(app.main.app)
        response = client.post(
            "/public/v1/leads",
            headers={"X-API-Key": raw},
            json={
                "company_id": str(company.id),
                "title": "API lead",
                "source": "partner",
            },
        )
        listed = client.get("/public/v1/leads", headers={"X-API-Key": raw})
    finally:
        app.main.app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["title"] == "API lead"
    assert listed.status_code == 200
    assert [item["title"] for item in listed.json()] == ["API lead"]
