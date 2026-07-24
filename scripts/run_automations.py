from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import app.main  # noqa: E402,F401
from app.core.database import SessionLocal, set_tenant_context  # noqa: E402
from app.modules.accounts.models import Tenant  # noqa: E402
from app.modules.automation.service import AutomationEngine  # noqa: E402


def process_once() -> tuple[int, int]:
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

    return evaluated, matched


def main() -> None:
    parser = argparse.ArgumentParser(description="Process scheduled CRM automations")
    parser.add_argument("--loop", action="store_true", help="Keep polling until stopped")
    parser.add_argument(
        "--interval",
        type=float,
        default=60,
        help="Seconds between scheduled scans",
    )
    args = parser.parse_args()
    while True:
        evaluated, matched = process_once()
        print(
            f"Scheduled automation complete: evaluated={evaluated}, matched={matched}",
            flush=True,
        )
        if not args.loop:
            return
        time.sleep(max(args.interval, 5))


if __name__ == "__main__":
    main()
