import json
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
from app.core.rbac import Permission, ROLE_PERMISSIONS, Role
from app.core.security import create_access_token, hash_password
from app.main import app
from app.modules.accounts.models import Membership, Tenant, User
from app.modules.ai_agent.models import AgentAction
from app.modules.sales.models import Company


PROTECTED_PREFIXES = (
    "/accounts",
    "/activities",
    "/ai-agent",
    "/automations",
    "/communication",
    "/connectors",
    "/knowledge",
    "/production",
    "/sales",
    "/templates",
)
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _dependency_calls(route: APIRoute) -> set[object]:
    calls: set[object] = set()
    pending = list(route.dependant.dependencies)
    while pending:
        dependency = pending.pop()
        if dependency.call is not None:
            calls.add(dependency.call)
        pending.extend(dependency.dependencies)
    return calls


def test_every_tenant_mutation_declares_a_permission():
    unprotected = []
    for route in app.routes:
        if not isinstance(route, APIRoute) or not route.path.startswith(PROTECTED_PREFIXES):
            continue
        if not (route.methods & UNSAFE_METHODS):
            continue
        if not any(hasattr(call, "required_permission") for call in _dependency_calls(route)):
            unprotected.append(f"{','.join(sorted(route.methods))} {route.path}")

    assert unprotected == []


def test_permission_matrix_is_fail_closed():
    assert set(ROLE_PERMISSIONS) == set(Role)
    assert ROLE_PERMISSIONS[Role.VIEWER] == {Permission.CRM_READ}
    assert Permission.BILLING_MANAGE in ROLE_PERMISSIONS[Role.OWNER]
    assert Permission.BILLING_MANAGE not in ROLE_PERMISSIONS[Role.ADMIN]
    assert Permission.FEATURE_FLAGS_MANAGE in ROLE_PERMISSIONS[Role.ADMIN]
    assert Permission.FEATURE_FLAGS_MANAGE not in ROLE_PERMISSIONS[Role.SALES_MANAGER]
    assert Permission.CRM_WRITE in ROLE_PERMISSIONS[Role.SALES_REP]
    assert Permission.AUTOMATIONS_MANAGE in ROLE_PERMISSIONS[Role.SALES_MANAGER]
    assert Permission.AUTOMATIONS_MANAGE not in ROLE_PERMISSIONS[Role.SALES_REP]


@pytest.fixture
def rbac_api() -> Generator[dict, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = Session(engine)
    tenant = Tenant(name="RBAC Tenant", slug=f"rbac-{uuid4()}")
    db.add(tenant)
    db.flush()

    users = {}
    memberships = {}
    for role in Role:
        user = User(
            email=f"{role.value}-{uuid4()}@example.com",
            full_name=role.value,
            password_hash=hash_password("password123"),
        )
        db.add(user)
        db.flush()
        membership = Membership(tenant_id=tenant.id, user_id=user.id, role=role)
        db.add(membership)
        users[role] = user
        memberships[role] = membership

    external_user = User(
        email=f"external-{uuid4()}@example.com",
        full_name="External User",
        password_hash=hash_password("password123"),
    )
    db.add(external_user)
    db.flush()
    own_company = Company(tenant_id=tenant.id, name="Rep Company", owner_id=users[Role.SALES_REP].id)
    other_company = Company(tenant_id=tenant.id, name="Other Company", owner_id=users[Role.OWNER].id)
    db.add_all([own_company, other_company])
    db.flush()
    foreign_target_action = AgentAction(
        tenant_id=tenant.id,
        user_id=users[Role.SALES_REP].id,
        action_type="create_task",
        status="pending",
        payload_json=json.dumps(
            {
                "company_id": str(other_company.id),
                "title": "Forbidden AI task",
            }
        ),
    )
    db.add(foreign_target_action)
    db.commit()

    def override_db() -> Generator[Session, None, None]:
        yield db

    app.dependency_overrides[get_db] = override_db
    try:
        yield {
            "client": TestClient(app),
            "db": db,
            "tenant": tenant,
            "users": users,
            "memberships": memberships,
            "external_user": external_user,
            "own_company": own_company,
            "other_company": other_company,
            "foreign_target_action": foreign_target_action,
        }
    finally:
        app.dependency_overrides.clear()
        db.close()


def _headers(data: dict, role: Role) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {create_access_token(data['users'][role].id)}",
        "X-Tenant-Id": str(data["tenant"].id),
    }


def test_viewer_can_read_but_cannot_create_crm_objects(rbac_api):
    client = rbac_api["client"]
    headers = _headers(rbac_api, Role.VIEWER)

    assert client.get("/sales/companies", headers=headers).status_code == 200
    response = client.post("/sales/companies", headers=headers, json={"name": "Denied Company"})

    assert response.status_code == 403
    assert response.json()["detail"] == "Permission denied"


def test_me_returns_effective_permissions(rbac_api):
    response = rbac_api["client"].get(
        "/me",
        headers=_headers(rbac_api, Role.SALES_REP),
    )

    assert response.status_code == 200
    assert response.json()["role"] == "sales_rep"
    assert set(response.json()["permissions"]) == {
        "crm:read",
        "crm:write",
        "ai:use",
        "knowledge:write",
    }


@pytest.mark.parametrize(
    ("role", "method", "path", "payload"),
    [
        (Role.VIEWER, "get", "/production/overview", None),
        (Role.SALES_REP, "get", "/production/audit", None),
        (Role.SALES_MANAGER, "post", "/connectors/accounts", {}),
        (Role.SALES_MANAGER, "post", "/templates/apply", {}),
        (Role.SALES_REP, "get", "/production/export", None),
        (Role.VIEWER, "get", "/accounts/members", None),
    ],
)
def test_non_admin_roles_cannot_use_administrative_endpoints(
    rbac_api,
    role,
    method,
    path,
    payload,
):
    response = rbac_api["client"].request(
        method,
        path,
        headers=_headers(rbac_api, role),
        json=payload,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Permission denied"


@pytest.mark.parametrize("role", [Role.ADMIN, Role.SALES_MANAGER, Role.SALES_REP, Role.VIEWER])
def test_only_owner_can_change_plan(rbac_api, role):
    response = rbac_api["client"].put(
        "/production/plan",
        headers=_headers(rbac_api, role),
        json={
            "plan_code": "pilot",
            "users_limit": 10,
            "leads_limit": 100,
            "documents_limit": 100,
            "ai_requests_limit": 1000,
        },
    )

    assert response.status_code == 403


def test_owner_can_change_plan(rbac_api):
    response = rbac_api["client"].put(
        "/production/plan",
        headers=_headers(rbac_api, Role.OWNER),
        json={
            "plan_code": "pilot",
            "users_limit": 10,
            "leads_limit": 100,
            "documents_limit": 100,
            "ai_requests_limit": 1000,
        },
    )

    assert response.status_code == 200
    assert response.json()["plan_code"] == "pilot"


def test_admin_can_manage_flags_but_sales_manager_cannot(rbac_api):
    payload = {"code": "rbac-pilot", "title": "RBAC pilot", "enabled": True}

    denied = rbac_api["client"].post(
        "/production/flags",
        headers=_headers(rbac_api, Role.SALES_MANAGER),
        json=payload,
    )
    allowed = rbac_api["client"].post(
        "/production/flags",
        headers=_headers(rbac_api, Role.ADMIN),
        json=payload,
    )

    assert denied.status_code == 403
    assert allowed.status_code == 201


def test_sales_rep_can_only_update_owned_company(rbac_api):
    headers = _headers(rbac_api, Role.SALES_REP)

    allowed = rbac_api["client"].patch(
        f"/sales/companies/{rbac_api['own_company'].id}",
        headers=headers,
        json={"description": "Rep update"},
    )
    denied = rbac_api["client"].patch(
        f"/sales/companies/{rbac_api['other_company'].id}",
        headers=headers,
        json={"description": "Forbidden update"},
    )

    assert allowed.status_code == 200
    assert denied.status_code == 403
    assert denied.json()["detail"] == "Object access denied"


def test_sales_rep_cannot_change_manager_fields(rbac_api):
    response = rbac_api["client"].patch(
        f"/sales/companies/{rbac_api['own_company'].id}",
        headers=_headers(rbac_api, Role.SALES_REP),
        json={"health_score": 99},
    )

    assert response.status_code == 403
    assert "health_score" in response.json()["detail"]


def test_sales_rep_cannot_create_activity_for_unowned_company(rbac_api):
    response = rbac_api["client"].post(
        "/activities",
        headers=_headers(rbac_api, Role.SALES_REP),
        json={
            "company_id": str(rbac_api["other_company"].id),
            "type": "call",
            "title": "Forbidden activity",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Object access denied"


def test_ai_confirmation_rechecks_target_object_access(rbac_api):
    response = rbac_api["client"].post(
        f"/ai-agent/actions/{rbac_api['foreign_target_action'].id}/confirm",
        headers=_headers(rbac_api, Role.SALES_REP),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Object access denied"
    rbac_api["db"].refresh(rbac_api["foreign_target_action"])
    assert rbac_api["foreign_target_action"].status == "pending"


def test_sales_manager_can_change_manager_fields_on_any_company(rbac_api):
    response = rbac_api["client"].patch(
        f"/sales/companies/{rbac_api['other_company'].id}",
        headers=_headers(rbac_api, Role.SALES_MANAGER),
        json={"health_score": 91},
    )

    assert response.status_code == 200
    assert response.json()["health_score"] == 91


def test_admin_cannot_grant_owner_role(rbac_api):
    membership = rbac_api["memberships"][Role.SALES_REP]
    response = rbac_api["client"].patch(
        f"/accounts/members/{membership.id}",
        headers=_headers(rbac_api, Role.ADMIN),
        json={"role": "owner"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Only an owner can manage privileged roles"


def test_owner_can_add_existing_user_with_sales_role(rbac_api):
    response = rbac_api["client"].post(
        "/accounts/members",
        headers=_headers(rbac_api, Role.OWNER),
        json={"email": rbac_api["external_user"].email, "role": "sales_rep"},
    )

    assert response.status_code == 201
    assert response.json()["role"] == "sales_rep"
    assert response.json()["email"] == rbac_api["external_user"].email


def test_last_owner_cannot_be_demoted(rbac_api):
    membership = rbac_api["memberships"][Role.OWNER]
    response = rbac_api["client"].patch(
        f"/accounts/members/{membership.id}",
        headers=_headers(rbac_api, Role.OWNER),
        json={"role": "admin"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "The last owner cannot be demoted"
