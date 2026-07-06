import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import CurrentTenant, get_current_tenant
from app.modules.production.models import AuditLog, FeatureFlag, TenantPlan
from app.modules.production.schemas import (
    AuditLogResponse,
    DataExportResponse,
    FeatureFlagCreate,
    FeatureFlagResponse,
    FeatureFlagUpdate,
    ProductionOverviewResponse,
    TenantPlanResponse,
    TenantPlanUpdate,
)
from app.modules.production.service import ProductionService


router = APIRouter()


@router.get("/overview", response_model=ProductionOverviewResponse)
def overview(
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> dict:
    return ProductionService(db).overview(tenant.id)


@router.get("/audit", response_model=list[AuditLogResponse])
def audit(
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> list[AuditLogResponse]:
    return [_audit_response(row) for row in ProductionService(db).list_audit(tenant.id)]


@router.post("/audit", response_model=AuditLogResponse, status_code=status.HTTP_201_CREATED)
def create_audit_marker(
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> AuditLogResponse:
    row = ProductionService(db).log(
        tenant_id=tenant.id,
        user_id=tenant.user_id,
        action="manual_audit_marker",
        entity_type="production",
        payload={"source": "production_page"},
    )
    return _audit_response(row)


@router.get("/flags", response_model=list[FeatureFlagResponse])
def flags(
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> list[FeatureFlagResponse]:
    return [_flag_response(flag) for flag in ProductionService(db).list_flags(tenant.id)]


@router.post("/flags", response_model=FeatureFlagResponse, status_code=status.HTTP_201_CREATED)
def create_flag(
    payload: FeatureFlagCreate,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> FeatureFlagResponse:
    service = ProductionService(db)
    flag = service.create_flag(tenant.id, payload.code, payload.title, payload.enabled)
    service.log(tenant.id, tenant.user_id, "feature_flag_upsert", "feature_flag", str(flag.id), {"code": flag.code})
    return _flag_response(flag)


@router.patch("/flags/{flag_id}", response_model=FeatureFlagResponse)
def update_flag(
    flag_id: UUID,
    payload: FeatureFlagUpdate,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> FeatureFlagResponse:
    service = ProductionService(db)
    flag = service.update_flag(tenant.id, flag_id, payload.enabled)
    if not flag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature flag not found")
    service.log(tenant.id, tenant.user_id, "feature_flag_update", "feature_flag", str(flag.id), {"enabled": flag.enabled})
    return _flag_response(flag)


@router.get("/plan", response_model=TenantPlanResponse)
def get_plan(
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> TenantPlanResponse:
    return _plan_response(ProductionService(db).get_or_create_plan(tenant.id))


@router.put("/plan", response_model=TenantPlanResponse)
def update_plan(
    payload: TenantPlanUpdate,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> TenantPlanResponse:
    service = ProductionService(db)
    plan = service.update_plan(tenant.id, payload)
    service.log(tenant.id, tenant.user_id, "tenant_plan_update", "tenant_plan", str(plan.id), {"plan_code": plan.plan_code})
    return _plan_response(plan)


@router.get("/export", response_model=DataExportResponse)
def export_data(
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> DataExportResponse:
    service = ProductionService(db)
    data = service.export_tenant_data(tenant.id)
    service.log(tenant.id, tenant.user_id, "tenant_data_export", "tenant", str(tenant.id), {"format": "json"})
    return DataExportResponse(filename="tenant-export.json", data=data)


def _audit_response(row: AuditLog) -> AuditLogResponse:
    return AuditLogResponse(
        id=row.id,
        user_id=row.user_id,
        action=row.action,
        entity_type=row.entity_type,
        entity_id=row.entity_id,
        payload=json.loads(row.payload_json),
        created_at=row.created_at,
    )


def _flag_response(flag: FeatureFlag) -> FeatureFlagResponse:
    return FeatureFlagResponse(
        id=flag.id,
        code=flag.code,
        title=flag.title,
        enabled=flag.enabled,
        created_at=flag.created_at,
    )


def _plan_response(plan: TenantPlan) -> TenantPlanResponse:
    return TenantPlanResponse(
        id=plan.id,
        plan_code=plan.plan_code,
        users_limit=plan.users_limit,
        leads_limit=plan.leads_limit,
        documents_limit=plan.documents_limit,
        ai_requests_limit=plan.ai_requests_limit,
        created_at=plan.created_at,
    )

