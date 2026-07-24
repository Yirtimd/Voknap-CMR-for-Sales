from collections.abc import Generator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.main  # noqa: F401 - registers all models
from app.core.database import Base, get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.modules.accounts.models import Membership, Tenant, User
from app.modules.sales.models import Company, Contact, Deal, Lead, Note, Pipeline, PipelineStage, Task


@pytest.fixture
def lifecycle_api() -> Generator[dict, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = Session(engine)
    tenant = Tenant(name="Lifecycle Tenant", slug=f"lifecycle-{uuid4()}")
    owner = User(
        email=f"owner-{uuid4()}@example.com",
        full_name="Owner",
        password_hash=hash_password("password123"),
    )
    rep = User(
        email=f"rep-{uuid4()}@example.com",
        full_name="Sales Rep",
        password_hash=hash_password("password123"),
    )
    db.add_all([tenant, owner, rep])
    db.flush()
    db.add_all(
        [
            Membership(tenant_id=tenant.id, user_id=owner.id, role="owner"),
            Membership(tenant_id=tenant.id, user_id=rep.id, role="sales_rep"),
        ]
    )
    company = Company(tenant_id=tenant.id, name="Lifecycle Company", owner_id=rep.id)
    db.add(company)
    db.flush()
    contact = Contact(
        tenant_id=tenant.id,
        company_id=company.id,
        name="Primary Contact",
        email="primary@example.com",
        owner_id=rep.id,
    )
    duplicate_contact = Contact(
        tenant_id=tenant.id,
        company_id=company.id,
        name="Duplicate Contact",
        email="duplicate@example.com",
        owner_id=rep.id,
    )
    pipeline = Pipeline(tenant_id=tenant.id, name="Sales")
    db.add_all([contact, duplicate_contact, pipeline])
    db.flush()
    stage = PipelineStage(tenant_id=tenant.id, pipeline_id=pipeline.id, name="Open", sort_order=0)
    lead = Lead(
        tenant_id=tenant.id,
        company_id=company.id,
        contact_id=duplicate_contact.id,
        title="Lifecycle Lead",
        source="web",
        owner_id=rep.id,
    )
    db.add_all([stage, lead])
    db.flush()
    deal = Deal(
        tenant_id=tenant.id,
        company_id=company.id,
        lead_id=lead.id,
        stage_id=stage.id,
        title="Lifecycle Deal",
        amount=1000,
        owner_id=rep.id,
    )
    task = Task(
        tenant_id=tenant.id,
        company_id=company.id,
        assigned_to_id=rep.id,
        title="Lifecycle Task",
    )
    note = Note(
        tenant_id=tenant.id,
        company_id=company.id,
        lead_id=lead.id,
        author_id=rep.id,
        text="Lifecycle note",
    )
    db.add_all([deal, task, note])
    db.commit()

    def override_db() -> Generator[Session, None, None]:
        yield db

    app.dependency_overrides[get_db] = override_db
    try:
        yield {
            "client": TestClient(app),
            "db": db,
            "tenant": tenant,
            "owner": owner,
            "rep": rep,
            "company": company,
            "contact": contact,
            "duplicate_contact": duplicate_contact,
            "lead": lead,
            "deal": deal,
            "task": task,
            "note": note,
            "stage": stage,
        }
    finally:
        app.dependency_overrides.clear()
        db.close()


def _headers(data: dict, user_key: str = "rep") -> dict[str, str]:
    return {
        "Authorization": f"Bearer {create_access_token(data[user_key].id)}",
        "X-Tenant-Id": str(data["tenant"].id),
    }


def test_contact_update_records_history_and_rejects_stale_version(lifecycle_api):
    contact = lifecycle_api["contact"]
    response = lifecycle_api["client"].patch(
        f"/sales/contacts/{contact.id}",
        headers=_headers(lifecycle_api),
        json={"version": contact.version, "phone": "+7-900-000-00-00"},
    )

    assert response.status_code == 200
    assert response.json()["version"] == 2
    stale = lifecycle_api["client"].patch(
        f"/sales/contacts/{contact.id}",
        headers=_headers(lifecycle_api),
        json={"version": 1, "phone": "+7-900-111-11-11"},
    )
    assert stale.status_code == 409

    history = lifecycle_api["client"].get(
        f"/sales/contacts/{contact.id}/history",
        headers=_headers(lifecycle_api),
    )
    assert history.status_code == 200
    assert history.json()[0]["field_name"] == "phone"
    assert history.json()[0]["entity_version"] == 2


def test_lead_deal_task_and_note_support_versioned_editing(lifecycle_api):
    cases = (
        ("leads", lifecycle_api["lead"], {"title": "Updated lead"}),
        ("deals", lifecycle_api["deal"], {"title": "Updated deal"}),
        ("tasks", lifecycle_api["task"], {"title": "Updated task"}),
        ("notes", lifecycle_api["note"], {"text": "Updated note"}),
    )
    for resource, entity, changes in cases:
        response = lifecycle_api["client"].patch(
            f"/sales/{resource}/{entity.id}",
            headers=_headers(lifecycle_api),
            json={"version": entity.version, **changes},
        )
        assert response.status_code == 200, response.json()
        assert response.json()["version"] == 2


def test_archive_search_pagination_and_restore(lifecycle_api):
    contact = lifecycle_api["contact"]
    archived = lifecycle_api["client"].patch(
        f"/sales/contacts/{contact.id}/archive",
        headers=_headers(lifecycle_api),
        json={"version": contact.version, "is_archived": True},
    )
    assert archived.status_code == 200

    active_list = lifecycle_api["client"].get(
        "/sales/contacts?search=Primary&page=1&page_size=1",
        headers=_headers(lifecycle_api),
    )
    assert active_list.status_code == 200
    assert active_list.json() == []
    assert active_list.headers["x-total-count"] == "0"

    archive_list = lifecycle_api["client"].get(
        "/sales/contacts?search=Primary&include_archived=true&page=1&page_size=1&sort=name&order=asc",
        headers=_headers(lifecycle_api),
    )
    assert archive_list.status_code == 200
    assert archive_list.json()[0]["id"] == str(contact.id)
    assert archive_list.headers["x-page-size"] == "1"

    deleted = lifecycle_api["client"].delete(
        f"/sales/contacts/{contact.id}?version={archived.json()['version']}",
        headers=_headers(lifecycle_api),
    )
    assert deleted.status_code == 200
    assert (
        lifecycle_api["client"].get(
            f"/sales/contacts/{contact.id}",
            headers=_headers(lifecycle_api),
        ).status_code
        == 404
    )
    assert (
        lifecycle_api["client"].get(
            "/sales/contacts?include_deleted=true&include_archived=true",
            headers=_headers(lifecycle_api),
        ).status_code
        == 403
    )
    deleted_list = lifecycle_api["client"].get(
        "/sales/contacts?include_deleted=true&include_archived=true",
        headers=_headers(lifecycle_api, "owner"),
    )
    assert deleted_list.status_code == 200
    assert str(contact.id) in {row["id"] for row in deleted_list.json()}
    restored = lifecycle_api["client"].post(
        f"/sales/contacts/{contact.id}/restore",
        headers=_headers(lifecycle_api),
        json={"version": deleted.json()["version"]},
    )
    assert restored.status_code == 200
    assert restored.json()["deleted_at"] is None


def test_lead_qualification_and_conversion(lifecycle_api):
    lead = lifecycle_api["lead"]
    qualified = lifecycle_api["client"].post(
        f"/sales/leads/{lead.id}/qualify",
        headers=_headers(lifecycle_api),
        json={"version": lead.version, "qualified": True},
    )
    assert qualified.status_code == 200
    assert qualified.json()["status"] == "qualified"

    converted = lifecycle_api["client"].post(
        f"/sales/leads/{lead.id}/convert",
        headers=_headers(lifecycle_api),
        json={
            "version": qualified.json()["version"],
            "stage_id": str(lifecycle_api["stage"].id),
            "amount": 2500,
        },
    )
    assert converted.status_code == 200
    assert converted.json()["lead"]["status"] == "converted"
    assert converted.json()["lead"]["converted_deal_id"] == converted.json()["deal"]["id"]
    assert converted.json()["deal"]["amount"] == 2500


def test_contact_merge_rewires_relations_and_soft_deletes_source(lifecycle_api):
    target = lifecycle_api["contact"]
    source = lifecycle_api["duplicate_contact"]
    response = lifecycle_api["client"].post(
        f"/sales/contacts/{target.id}/merge",
        headers=_headers(lifecycle_api),
        json={
            "target_version": target.version,
            "sources": [{"id": str(source.id), "version": source.version}],
        },
    )

    assert response.status_code == 200
    lifecycle_api["db"].expire_all()
    lead = lifecycle_api["db"].get(Lead, lifecycle_api["lead"].id)
    merged_source = (
        lifecycle_api["db"]
        .query(Contact)
        .execution_options(include_deleted=True, include_archived=True)
        .filter(Contact.id == source.id)
        .one()
    )
    assert lead.contact_id == target.id
    assert merged_source.deleted_at is not None


def test_duplicate_scan_persists_candidate_and_merge_resolves_it(lifecycle_api):
    lifecycle_api["duplicate_contact"].email = lifecycle_api["contact"].email
    lifecycle_api["db"].commit()
    scanned = lifecycle_api["client"].post(
        "/sales/dedup/scan",
        headers=_headers(lifecycle_api, "owner"),
        json={"entity_type": "contacts", "minimum_score": 80},
    )
    assert scanned.status_code == 200, scanned.text
    candidates = lifecycle_api["client"].get(
        "/sales/dedup/candidates?entity_type=contacts",
        headers=_headers(lifecycle_api, "owner"),
    )
    assert candidates.status_code == 200
    candidate = candidates.json()[0]
    assert candidate["score"] == 100
    assert "email" in candidate["matched_fields"]

    merged = lifecycle_api["client"].post(
        f"/sales/contacts/{lifecycle_api['contact'].id}/merge",
        headers=_headers(lifecycle_api),
        json={
            "target_version": lifecycle_api["contact"].version,
            "sources": [
                {
                    "id": str(lifecycle_api["duplicate_contact"].id),
                    "version": lifecycle_api["duplicate_contact"].version,
                }
            ],
        },
    )
    assert merged.status_code == 200, merged.text
    resolved = lifecycle_api["client"].get(
        "/sales/dedup/candidates?entity_type=contacts&status=merged",
        headers=_headers(lifecycle_api, "owner"),
    )
    assert resolved.status_code == 200
    assert resolved.json()[0]["id"] == candidate["id"]


def test_bulk_archive_and_owner_reassignment(lifecycle_api):
    task = lifecycle_api["task"]
    archived = lifecycle_api["client"].post(
        "/sales/tasks/bulk",
        headers=_headers(lifecycle_api, "owner"),
        json={
            "action": "archive",
            "items": [{"id": str(task.id), "version": task.version}],
        },
    )
    assert archived.status_code == 200
    assert archived.json()["affected"] == 1

    lifecycle_api["db"].refresh(task)
    reassigned = lifecycle_api["client"].patch(
        f"/sales/tasks/{task.id}/owner",
        headers=_headers(lifecycle_api, "owner"),
        json={"version": task.version, "owner_id": str(lifecycle_api["owner"].id)},
    )
    assert reassigned.status_code == 200
    lifecycle_api["db"].refresh(task)
    assert task.assigned_to_id == lifecycle_api["owner"].id
