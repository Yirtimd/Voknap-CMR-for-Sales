import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from app.core.config import settings


pytestmark = pytest.mark.postgres


@pytest.fixture
def postgres_connection():
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.fail("TEST_DATABASE_URL is required for PostgreSQL integration tests")
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            tenant_a = uuid4()
            tenant_b = uuid4()
            company_a = uuid4()
            company_b = uuid4()
            connection.execute(
                text(
                    "INSERT INTO tenants (id, name, slug, is_active, created_at) VALUES "
                    "(:tenant_a, 'Tenant A', :slug_a, true, now()), "
                    "(:tenant_b, 'Tenant B', :slug_b, true, now())"
                ),
                {
                    "tenant_a": tenant_a,
                    "tenant_b": tenant_b,
                    "slug_a": f"rls-a-{tenant_a}",
                    "slug_b": f"rls-b-{tenant_b}",
                },
            )
            connection.execute(
                text(
                    "INSERT INTO companies (id, tenant_id, name, status, created_at) VALUES "
                    "(:company_a, :tenant_a, 'Company A', 'active', now()), "
                    "(:company_b, :tenant_b, 'Company B', 'active', now())"
                ),
                {
                    "company_a": company_a,
                    "company_b": company_b,
                    "tenant_a": tenant_a,
                    "tenant_b": tenant_b,
                },
            )
            try:
                yield connection, tenant_a, tenant_b, company_a, company_b
            finally:
                transaction.rollback()
    finally:
        engine.dispose()


def test_rls_default_deny_and_tenant_scope(postgres_connection):
    connection, tenant_a, _tenant_b, _company_a, _company_b = postgres_connection
    connection.exec_driver_sql(f'SET LOCAL ROLE "{settings.database_runtime_role}"')
    assert connection.execute(text("SELECT count(*) FROM companies")).scalar_one() == 0

    connection.execute(
        text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
        {"tenant_id": str(tenant_a)},
    )
    visible_tenants = connection.execute(
        text("SELECT DISTINCT tenant_id FROM companies")
    ).scalars().all()
    assert visible_tenants == [tenant_a]


def test_composite_fk_rejects_cross_tenant_reference(postgres_connection):
    connection, tenant_a, _tenant_b, _company_a, company_b = postgres_connection
    connection.exec_driver_sql(f'SET LOCAL ROLE "{settings.database_runtime_role}"')
    connection.execute(
        text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
        {"tenant_id": str(tenant_a)},
    )
    with pytest.raises(IntegrityError):
        connection.execute(
            text(
                "INSERT INTO contacts "
                "(id, tenant_id, company_id, name, can_call, can_email, "
                "can_open_more, created_at) "
                "VALUES (:id, :tenant_id, :company_id, 'cross-tenant', "
                "true, true, true, now())"
            ),
            {
                "id": uuid4(),
                "tenant_id": tenant_a,
                "company_id": company_b,
            },
        )


def test_team_management_tables_are_default_deny(postgres_connection):
    connection, tenant_a, tenant_b, _company_a, _company_b = postgres_connection
    connection.execute(
        text(
            "INSERT INTO sales_teams "
            "(id, tenant_id, name, is_active, created_at) VALUES "
            "(:team_a, :tenant_a, 'Team A', true, now()), "
            "(:team_b, :tenant_b, 'Team B', true, now())"
        ),
        {
            "team_a": uuid4(),
            "team_b": uuid4(),
            "tenant_a": tenant_a,
            "tenant_b": tenant_b,
        },
    )
    connection.exec_driver_sql(f'SET LOCAL ROLE "{settings.database_runtime_role}"')
    assert connection.execute(text("SELECT count(*) FROM sales_teams")).scalar_one() == 0
    connection.execute(
        text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
        {"tenant_id": str(tenant_a)},
    )
    assert connection.execute(text("SELECT name FROM sales_teams")).scalar_one() == "Team A"


def test_queue_rejects_cross_tenant_team(postgres_connection):
    connection, tenant_a, tenant_b, _company_a, _company_b = postgres_connection
    team_b = uuid4()
    connection.execute(
        text(
            "INSERT INTO sales_teams (id, tenant_id, name, is_active, created_at) "
            "VALUES (:id, :tenant_id, 'Foreign team', true, now())"
        ),
        {"id": team_b, "tenant_id": tenant_b},
    )
    connection.exec_driver_sql(f'SET LOCAL ROLE "{settings.database_runtime_role}"')
    connection.execute(
        text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
        {"tenant_id": str(tenant_a)},
    )
    with pytest.raises(IntegrityError):
        connection.execute(
            text(
                "INSERT INTO lead_queues "
                "(id, tenant_id, name, team_id, strategy, routing_cursor, is_active, created_at) "
                "VALUES (:id, :tenant_id, 'Cross tenant', :team_id, "
                "'manual', 0, true, now())"
            ),
            {"id": uuid4(), "tenant_id": tenant_a, "team_id": team_b},
        )
