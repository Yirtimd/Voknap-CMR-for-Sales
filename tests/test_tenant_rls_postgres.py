import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from app.core.config import settings


pytestmark = pytest.mark.postgres


@pytest.fixture
def postgres_engine():
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is required")
    engine = create_engine(database_url)
    try:
        yield engine
    finally:
        engine.dispose()


def test_rls_default_deny_and_tenant_scope(postgres_engine):
    with postgres_engine.connect() as connection:
        transaction = connection.begin()
        try:
            connection.exec_driver_sql(f'SET LOCAL ROLE "{settings.database_runtime_role}"')
            assert connection.execute(text("SELECT count(*) FROM companies")).scalar_one() == 0

            tenant_id = connection.execute(
                text("SELECT id FROM tenants WHERE slug = 'developer-test'")
            ).scalar_one()
            connection.execute(
                text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
                {"tenant_id": str(tenant_id)},
            )
            visible_tenants = connection.execute(
                text("SELECT DISTINCT tenant_id FROM companies")
            ).scalars().all()
            assert set(visible_tenants) <= {tenant_id}
        finally:
            transaction.rollback()


def test_composite_fk_rejects_cross_tenant_reference(postgres_engine):
    with postgres_engine.connect() as connection:
        tenants = connection.execute(
            text(
                "SELECT c.tenant_id, c.id FROM companies c "
                "ORDER BY c.tenant_id, c.id"
            )
        ).all()
        tenant_a, company_b = next(
            (left[0], right[1])
            for left in tenants
            for right in tenants
            if left[0] != right[0]
        )

        transaction = connection.begin_nested()
        try:
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
        finally:
            transaction.rollback()
