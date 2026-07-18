from collections.abc import Generator
from uuid import uuid4

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.main  # noqa: F401 - registers all models
from app.core.database import Base, get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.modules.accounts.models import Membership, Tenant, User
from app.modules.knowledge.models import KnowledgeDocument
from app.modules.sales.models import Company, Lead


PROTECTED_PREFIXES = (
    "/accounts",
    "/activities",
    "/ai-agent",
    "/analytics",
    "/communication",
    "/connectors",
    "/knowledge",
    "/production",
    "/sales",
    "/templates",
)


def _dependency_calls(route: APIRoute) -> set[object]:
    calls: set[object] = set()
    pending = list(route.dependant.dependencies)
    while pending:
        dependency = pending.pop()
        if dependency.call is not None:
            calls.add(dependency.call)
        pending.extend(dependency.dependencies)
    return calls


def test_every_tenant_endpoint_requires_tenant_dependency():
    from app.core.dependencies import get_current_tenant

    unprotected = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if route.path == "/me" or route.path.startswith(PROTECTED_PREFIXES):
            if get_current_tenant not in _dependency_calls(route):
                unprotected.append(f"{','.join(sorted(route.methods))} {route.path}")

    assert unprotected == []


def test_every_tenant_model_declares_database_isolation_constraints():
    missing = []
    for table in Base.metadata.tables.values():
        if "tenant_id" not in table.c or table.name == "memberships":
            continue
        constraint_names = {constraint.name for constraint in table.constraints}
        required = {f"fk_{table.name}_tenant", f"uq_{table.name}_tenant_id"}
        if not required <= constraint_names:
            missing.append(table.name)

    assert missing == []


@pytest.fixture
def tenant_api() -> Generator[dict, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = Session(engine)

    tenant_a = Tenant(name="Tenant A", slug=f"tenant-a-{uuid4()}")
    tenant_b = Tenant(name="Tenant B", slug=f"tenant-b-{uuid4()}")
    user_a = User(
        email=f"a-{uuid4()}@example.com",
        full_name="Owner A",
        password_hash=hash_password("password123"),
    )
    user_b = User(
        email=f"b-{uuid4()}@example.com",
        full_name="Owner B",
        password_hash=hash_password("password123"),
    )
    db.add_all([tenant_a, tenant_b, user_a, user_b])
    db.flush()
    db.add_all(
        [
            Membership(tenant_id=tenant_a.id, user_id=user_a.id, role="owner"),
            Membership(tenant_id=tenant_b.id, user_id=user_b.id, role="owner"),
        ]
    )
    company_b = Company(tenant_id=tenant_b.id, name="Private Company B")
    db.add(company_b)
    db.flush()
    lead_b = Lead(tenant_id=tenant_b.id, company_id=company_b.id, title="Private Lead B")
    document_b = KnowledgeDocument(
        tenant_id=tenant_b.id,
        company_id=company_b.id,
        title="Private Document B",
        visibility="company",
    )
    db.add_all([lead_b, document_b])
    db.commit()

    def override_db() -> Generator[Session, None, None]:
        yield db

    app.dependency_overrides[get_db] = override_db
    try:
        yield {
            "client": TestClient(app),
            "tenant_a": tenant_a,
            "tenant_b": tenant_b,
            "user_a": user_a,
            "company_b": company_b,
            "lead_b": lead_b,
            "document_b": document_b,
        }
    finally:
        app.dependency_overrides.clear()
        db.close()


def _headers(user: User, tenant: Tenant) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {create_access_token(user.id)}",
        "X-Tenant-Id": str(tenant.id),
    }


@pytest.mark.parametrize(
    "path",
    [
        "/me",
        "/activities",
        "/ai-agent/history",
        "/analytics/overview",
        "/communication/events",
        "/connectors/definitions",
        "/knowledge/documents",
        "/production/overview",
        "/sales/companies",
        "/templates",
    ],
)
def test_each_router_rejects_tenant_without_membership(tenant_api, path):
    response = tenant_api["client"].get(
        path,
        headers=_headers(tenant_api["user_a"], tenant_api["tenant_b"]),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Tenant access denied"


@pytest.mark.parametrize(
    ("path_key", "path_template"),
    [
        ("company_b", "/sales/companies/{id}"),
        ("lead_b", "/sales/leads/{id}"),
        ("document_b", "/knowledge/documents/{id}"),
    ],
)
def test_object_ids_from_another_tenant_are_not_visible(tenant_api, path_key, path_template):
    foreign_object = tenant_api[path_key]
    response = tenant_api["client"].get(
        path_template.format(id=foreign_object.id),
        headers=_headers(tenant_api["user_a"], tenant_api["tenant_a"]),
    )

    assert response.status_code == 404
