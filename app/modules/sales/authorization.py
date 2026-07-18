from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import CurrentTenant
from app.core.rbac import require_object_owner
from app.modules.sales.models import Company, Deal


def require_company_write_access(
    db: Session,
    tenant: CurrentTenant,
    company_id: UUID,
) -> Company:
    company = (
        db.query(Company)
        .filter(Company.id == company_id, Company.tenant_id == tenant.id)
        .one_or_none()
    )
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    require_object_owner(tenant.role, tenant.user_id, company.owner_id)
    return company


def require_deal_write_access(
    db: Session,
    tenant: CurrentTenant,
    deal_id: UUID,
) -> Deal:
    deal = (
        db.query(Deal)
        .filter(Deal.id == deal_id, Deal.tenant_id == tenant.id)
        .one_or_none()
    )
    if deal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")
    require_object_owner(tenant.role, tenant.user_id, deal.owner_id)
    return deal

