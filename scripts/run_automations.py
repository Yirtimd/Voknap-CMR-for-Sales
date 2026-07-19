from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import app.main  # noqa: E402,F401
from app.core.database import SessionLocal, set_tenant_context  # noqa: E402
from app.modules.accounts.models import Tenant  # noqa: E402
from app.modules.automation.service import AutomationEngine  # noqa: E402


def main() -> None:
    with SessionLocal() as control_db:
        tenant_ids = [row.id for row in control_db.query(Tenant).filter(Tenant.is_active.is_(True))]

    evaluated = 0
    matched = 0
    for tenant_id in tenant_ids:
        with SessionLocal() as tenant_db:
            tenant_db.info["enforce_tenant_rls"] = True
            set_tenant_context(tenant_db, tenant_id)
            tenant_evaluated, tenant_matched = AutomationEngine(tenant_db).run_scheduled(
                tenant_id,
                None,
            )
            evaluated += tenant_evaluated
            matched += tenant_matched

    print(f"Scheduled automation complete: evaluated={evaluated}, matched={matched}")


if __name__ == "__main__":
    main()
